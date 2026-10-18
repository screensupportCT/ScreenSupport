import customtkinter as ctk
import threading
import asyncio
import websockets
import json
import base64
import io
from mss import mss
from PIL import Image
import pyautogui
import ctypes

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00008000)  # ABOVE_NORMAL
except Exception:
    pass

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# Poné acá la dirección de tu propio servidor (ver server.js en este repo)
SERVIDOR = "wss://TU-SERVIDOR-AQUI"
ANCHO_PANTALLA, ALTO_PANTALLA = pyautogui.size()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("ScreenSupport - Cliente")
app.geometry("360x480")
app.configure(fg_color="#14181F")

titulo = ctk.CTkLabel(app, text="ScreenSupport", font=("Arial", 22, "bold"))
titulo.pack(pady=(40, 10))

codigo_label = ctk.CTkLabel(app, text="", font=("Arial", 40, "bold"))
codigo_label.pack(pady=20)

estado_label = ctk.CTkLabel(app, text="Sin conectar", text_color="#8A93A3")
estado_label.pack(pady=10)

boton = ctk.CTkButton(app, text="Generar código", command=lambda: iniciar(), height=44, width=200)
boton.pack(pady=20)

boton_cortar = ctk.CTkButton(
    app, text="Cortar ahora", command=lambda: cortar_sesion(),
    fg_color="#D9634F", hover_color="#B8503F", height=36, width=160
)

ws_global = None
loop_global = None
compartiendo = False
tarea_envio = None

TECLAS_ESPECIALES = {
    "Return": "enter", "BackSpace": "backspace", "Tab": "tab",
    "Escape": "esc", "space": "space",
    "Up": "up", "Down": "down", "Left": "left", "Right": "right",
    "Delete": "delete", "Insert": "insert", "Home": "home", "End": "end",
    "Prior": "pageup", "Next": "pagedown",
    "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5", "F6": "f6",
    "F7": "f7", "F8": "f8", "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
    "Control_L": "ctrl", "Control_R": "ctrl",
    "Shift_L": "shift", "Shift_R": "shift",
    "Alt_L": "alt", "Alt_R": "alt",
    "Super_L": "win", "Super_R": "win",
    "Win_L": "win", "Win_R": "win",
}


def set_estado(texto, color="#8A93A3"):
    app.after(0, lambda: estado_label.configure(text=texto, text_color=color))


def set_codigo(texto):
    app.after(0, lambda: codigo_label.configure(text=texto))


def mostrar_boton_cortar():
    app.after(0, lambda: boton_cortar.pack(pady=10))


def ocultar_boton_cortar():
    app.after(0, boton_cortar.pack_forget)


def habilitar_boton_generar(hab=True):
    app.after(0, lambda: boton.configure(state="normal" if hab else "disabled"))


def capturar_pantalla_en_base64():
    with mss() as sct:
        try:
            monitor = sct.monitors[1]
        except IndexError:
            monitor = sct.monitors[0]
        captura = sct.grab(monitor)
        imagen = Image.frombytes("RGB", captura.size, captura.bgra, "raw", "BGRX")
        imagen.thumbnail((900, 650))
        buffer = io.BytesIO()
        imagen.save(buffer, format="JPEG", quality=40, optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def ejecutar_control(accion):
    try:
        tipo = accion.get("accion")
        if tipo == "mouse_down":
            x = int(accion["x"] * ANCHO_PANTALLA)
            y = int(accion["y"] * ALTO_PANTALLA)
            boton_click = accion.get("boton", "izq")
            pyautogui.moveTo(x, y)
            if boton_click == "izq":
                pyautogui.mouseDown(button='left')
            elif boton_click == "der":
                pyautogui.mouseDown(button='right')
            elif boton_click == "medio":
                pyautogui.mouseDown(button='middle')
            return

        elif tipo == "mouse_up":
            x = int(accion["x"] * ANCHO_PANTALLA)
            y = int(accion["y"] * ALTO_PANTALLA)
            boton_click = accion.get("boton", "izq")
            pyautogui.moveTo(x, y)
            if boton_click == "izq":
                pyautogui.mouseUp(button='left')
            elif boton_click == "der":
                pyautogui.mouseUp(button='right')
            elif boton_click == "medio":
                pyautogui.mouseUp(button='middle')
            return

        elif tipo == "click":
            x = int(accion["x"] * ANCHO_PANTALLA)
            y = int(accion["y"] * ALTO_PANTALLA)
            boton_click = accion.get("boton", "izq")
            pyautogui.moveTo(x, y)
            if boton_click == "izq":
                pyautogui.leftClick()
            elif boton_click == "der":
                pyautogui.rightClick()
            elif boton_click == "medio":
                pyautogui.middleClick()
            return

        elif tipo == "mover":
            x = int(accion["x"] * ANCHO_PANTALLA)
            y = int(accion["y"] * ALTO_PANTALLA)
            pyautogui.moveTo(x, y)
            return

        elif tipo == "arrastrar":
            x = int(accion["x"] * ANCHO_PANTALLA)
            y = int(accion["y"] * ALTO_PANTALLA)
            pyautogui.moveTo(x, y)
            return

        elif tipo == "scroll":
            delta = accion.get("delta", 0)
            if delta != 0:
                pyautogui.scroll(-int(delta / 120) * 3)
            return

        elif tipo == "tecla_char":
            tecla = accion.get("tecla")
            if tecla:
                pyautogui.write(tecla, interval=0)
            return

        elif tipo == "tecla":
            tecla = accion.get("tecla")
            if not tecla:
                return
            if tecla in TECLAS_ESPECIALES:
                pyautogui.press(TECLAS_ESPECIALES[tecla])
            else:
                pyautogui.press(tecla.lower())
            return

        elif tipo == "ctrl_combo":
            tecla = accion.get("tecla")
            if tecla in ['c', 'v', 'a', 's', 'g', 'z', 'x', 'e']:
                pyautogui.hotkey('ctrl', tecla, interval=0)
            return
    except Exception:
        pass


async def enviar_capturas(ws):
    global compartiendo
    while compartiendo:
        try:
            datos = capturar_pantalla_en_base64()
            await ws.send(json.dumps({"tipo": "frame", "datos": datos}))
            await asyncio.sleep(0.10)
        except Exception:
            await asyncio.sleep(0.5)


def cortar_sesion():
    global compartiendo, ws_global, loop_global
    compartiendo = False
    if ws_global and loop_global:
        try:
            asyncio.run_coroutine_threadsafe(ws_global.send(json.dumps({"tipo": "cortar_sesion"})), loop_global)
        except Exception:
            pass
    ws_global = None
    loop_global = None
    app.after(0, lambda: (
        set_codigo(""),
        set_estado("Sesión cortada"),
        ocultar_boton_cortar(),
        habilitar_boton_generar(True),
        boton.pack(pady=20),
        app.deiconify()
    ))


async def pedir_codigo():
    global compartiendo, ws_global, loop_global, tarea_envio
    loop_global = asyncio.get_running_loop()
    try:
        async with websockets.connect(SERVIDOR) as ws:
            ws_global = ws
            await ws.send(json.dumps({"tipo": "generar_codigo"}))
            while True:
                try:
                    respuesta = json.loads(await ws.recv())
                except websockets.exceptions.ConnectionClosed:
                    set_estado("Conexión perdida con el servidor", "#D9634F")
                    cortar_sesion()
                    break

                if respuesta["tipo"] == "codigo_generado":
                    codigo = respuesta["codigo"]
                    set_codigo(codigo[:3] + " " + codigo[3:])
                    set_estado("Esperando conexión del técnico...")
                    habilitar_boton_generar(False)
                    boton.pack_forget()

                elif respuesta["tipo"] == "conectado":
                    set_estado("Compartiendo pantalla", "#6FA8DC")
                    compartiendo = True
                    mostrar_boton_cortar()
                    app.after(0, app.iconify)
                    tarea_envio = asyncio.create_task(enviar_capturas(ws))

                elif respuesta["tipo"] == "control":
                    ejecutar_control(respuesta)

                elif respuesta["tipo"] == "sesion_cortada":
                    compartiendo = False
                    set_estado("Sesión cortada")
                    ocultar_boton_cortar()
                    habilitar_boton_generar(True)
                    set_codigo("")
                    boton.pack(pady=20)
                    app.after(0, app.deiconify)
                    break
    except Exception:
        set_estado("No se pudo conectar al servidor", "#D9634F")
        habilitar_boton_generar(True)
        boton.pack(pady=20)
        ocultar_boton_cortar()
        set_codigo("")
        app.after(0, app.deiconify)


def iniciar():
    set_estado("Conectando al servidor...")
    habilitar_boton_generar(False)

    def hilo():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(pedir_codigo())
        loop.close()

    threading.Thread(target=hilo, daemon=True).start()


app.mainloop()
