import tkinter as tk
import customtkinter as ctk
import threading
import asyncio
import websockets
import json
import base64
import io
import time
import ctypes
import tkinter.messagebox as messagebox
import pyperclip

try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00008000)  # ABOVE_NORMAL
except Exception:
    pass

from PIL import Image, ImageTk, ImageOps

# Poné acá la dirección de tu propio servidor (ver server.js en este repo)
SERVIDOR = "wss://episode-vessels-signals-liberty.trycloudflare.com"
VERSION = "V.1.0.1.0"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("ScreenSupport - Técnico")
app.geometry("900x650")
app.minsize(400, 400)
app.configure(fg_color="#14181F")

menu_top = ctk.CTkFrame(app, height=30, fg_color="#1C222E", corner_radius=0)
menu_top.pack(fill="x", side="top")
menu_top.pack_propagate(False)

titulo_menu = ctk.CTkLabel(menu_top, text=f"ScreenSupport • {VERSION}", font=("Arial", 9), text_color="#8A93A3")
titulo_menu.pack(side="left", padx=10)

frame_botones_menu = ctk.CTkFrame(menu_top, fg_color="transparent")
frame_botones_menu.pack(side="right", padx=4, pady=2)

boton_bloquear = ctk.CTkButton(
    frame_botones_menu, text="Bloquear entrada", width=110, height=22, font=("Arial", 8),
    command=lambda: toggle_bloqueo()
)
boton_bloquear.pack(side="left", padx=2)

boton_cerrar_sesion = ctk.CTkButton(
    frame_botones_menu, text="Cerrar sesión", width=95, height=22, font=("Arial", 8, "bold"),
    fg_color="#D9634F", hover_color="#B8503F", text_color="#FFFFFF",
    command=lambda: cerrar_sesion_tecnico()
)
boton_cerrar_sesion.pack(side="left", padx=2)

barra_superior = ctk.CTkFrame(app, fg_color="transparent")
barra_superior.pack(fill="x", padx=20, pady=(10, 6))

titulo = ctk.CTkLabel(barra_superior, text="ScreenSupport", font=("Arial", 20, "bold"))
titulo.pack(side="left")

fila_conexion = ctk.CTkFrame(app, fg_color="transparent")
fila_conexion.pack(fill="x", padx=40, pady=6)

entrada_codigo = ctk.CTkEntry(
    fila_conexion, placeholder_text="Código de 6 dígitos", font=("Arial", 18), height=40, justify="center"
)
entrada_codigo.pack(side="left", expand=True, fill="x", padx=(0, 10))

boton_conectar = ctk.CTkButton(fila_conexion, text="Conectar", command=lambda: al_hacer_clic(), height=40, width=120)
boton_conectar.pack(side="right")

estado_label = ctk.CTkLabel(app, text="", text_color="#8A93A3")
estado_label.pack(pady=4)

contenedor_pantalla = tk.Frame(app, bg="#14181F")
pantalla_label = tk.Label(contenedor_pantalla, bg="#0B0E14", bd=0)
pantalla_label.pack(expand=True, fill="both")

imagen_actual = None
imagen_original = None
ws_global = None
loop_global = None
conectado = False
ultimo_envio_mover = 0
ultimo_envio_tecla = 0
izq_presionado = False
maximizado = False
codigo_conectado = ""
tiempo_inicio = 0
entrada_bloqueada = False
ultimo_portapapeles = ""


def set_estado(texto, color="#8A93A3"):
    app.after(0, lambda: estado_label.configure(text=texto, text_color=color))


def actualizar_tiempo():
    if conectado and tiempo_inicio > 0:
        transcurrido = int(time.time() - tiempo_inicio)
        minutos, segundos = divmod(transcurrido, 60)
        horas, minutos = divmod(minutos, 60)
        tiempo_str = f"{horas:02d}:{minutos:02d}:{segundos:02d}" if horas > 0 else f"{minutos:02d}:{segundos:02d}"
        titulo_menu.configure(text=f"Conectado • Código: {codigo_conectado} • {VERSION} • {tiempo_str}")
        app.after(1000, actualizar_tiempo)


def toggle_bloqueo():
    global entrada_bloqueada
    if not conectado:
        return
    if not entrada_bloqueada:
        entrada_bloqueada = True
        boton_bloquear.configure(text="Desbloquear entrada", fg_color="#6FA8DC", hover_color="#5C9BD6")
        enviar_al_cliente({"tipo": "control", "accion": "bloquear_entrada"})
    else:
        entrada_bloqueada = False
        boton_bloquear.configure(text="Bloquear entrada", fg_color=("#3B8ED0", "#1F6AA5"), hover_color=("#36719F", "#144870"))
        enviar_al_cliente({"tipo": "control", "accion": "desbloquear_entrada"})


def sincronizar_portapapeles():
    global ultimo_portapapeles
    if not conectado:
        return
    try:
        texto = pyperclip.paste()
        if texto != ultimo_portapapeles and texto.strip() != "":
            ultimo_portapapeles = texto
            enviar_al_cliente({"tipo": "clipboard", "texto": texto})
    except Exception:
        pass
    app.after(500, sincronizar_portapapeles)


def redibujar_frame_actual(event=None):
    global imagen_actual
    if imagen_original is None:
        return
    ancho = pantalla_label.winfo_width()
    alto = pantalla_label.winfo_height()
    if ancho <= 0 or alto <= 0:
        return
    ajustada = ImageOps.contain(imagen_original, (ancho, alto), method=Image.LANCZOS)
    imagen_actual = ImageTk.PhotoImage(ajustada)
    pantalla_label.configure(image=imagen_actual)


def mostrar_frame(imagen_pil):
    global imagen_original

    def actualizar():
        global imagen_original
        if not contenedor_pantalla.winfo_ismapped():
            contenedor_pantalla.pack(expand=True, fill="both", padx=0, pady=0)
        imagen_original = imagen_pil
        redibujar_frame_actual()

    app.after(0, actualizar)


def ocultar_pantalla():
    app.after(0, contenedor_pantalla.pack_forget)


def limpiar_campo_codigo():
    def hacerlo():
        entrada_codigo.delete(0, "end")
        entrada_codigo.focus()
    app.after(0, hacerlo)


def habilitar_conexion(habilitar=True):
    def act():
        entrada_codigo.configure(state="normal" if habilitar else "disabled")
        boton_conectar.configure(state="normal" if habilitar else "disabled")
    app.after(0, act)


def ocultar_panel_conexion():
    app.after(0, lambda: (
        fila_conexion.pack_forget(),
        estado_label.pack_forget(),
        barra_superior.pack_forget()
    ))


def mostrar_panel_conexion():
    app.after(0, lambda: (
        barra_superior.pack(fill="x", padx=20, pady=(10, 6)),
        fila_conexion.pack(fill="x", padx=40, pady=6),
        estado_label.pack(pady=4)
    ))


def alternar_maximizado():
    global maximizado
    maximizado = not maximizado
    app.state("zoomed" if maximizado else "normal")


def cerrar_sesion_tecnico():
    if not conectado:
        return
    if not messagebox.askyesno("Cerrar sesión", "¿Seguro que querés cerrar esta sesión remota?"):
        return
    global ws_global, loop_global
    if ws_global and loop_global and conectado:
        try:
            asyncio.run_coroutine_threadsafe(ws_global.send(json.dumps({"tipo": "cortar_sesion"})), loop_global)
        except Exception:
            pass
    reset_estado()


def reset_estado():
    global conectado, ws_global, loop_global, imagen_original, imagen_actual, maximizado
    global izq_presionado, codigo_conectado, tiempo_inicio, entrada_bloqueada, ultimo_portapapeles
    conectado = False
    ws_global = None
    loop_global = None
    imagen_original = None
    imagen_actual = None
    maximizado = False
    izq_presionado = False
    codigo_conectado = ""
    tiempo_inicio = 0
    entrada_bloqueada = False
    ultimo_portapapeles = ""
    app.state("normal")
    boton_bloquear.configure(text="Bloquear entrada", fg_color=("#3B8ED0", "#1F6AA5"), hover_color=("#36719F", "#144870"))
    titulo_menu.configure(text=f"ScreenSupport • {VERSION}")
    pantalla_label.configure(image="")
    ocultar_pantalla()
    mostrar_panel_conexion()
    menu_top.pack(fill="x", side="top")
    habilitar_conexion(True)
    limpiar_campo_codigo()
    try:
        app.unbind_all("<MouseWheel>")
        app.unbind_all("<KeyPress-m>")
        app.unbind_all("<KeyPress-M>")
        app.unbind_all("<KeyPress-F11>")
        app.unbind_all("<KeyPress-Escape>")
        app.unbind_all("<KeyPress>")
        pantalla_label.unbind("<MouseWheel>")
        contenedor_pantalla.unbind("<MouseWheel>")
        pantalla_label.unbind("<Enter>")
    except Exception:
        pass


def enviar_al_cliente(mensaje):
    if ws_global and loop_global and conectado:
        try:
            asyncio.run_coroutine_threadsafe(ws_global.send(json.dumps(mensaje)), loop_global)
        except Exception:
            pass


def coordenadas_relativas(event):
    ancho = pantalla_label.winfo_width()
    alto = pantalla_label.winfo_height()
    if imagen_original is None or ancho == 0 or alto == 0:
        return None
    img_ancho, img_alto = imagen_original.size
    if img_ancho == 0 or img_alto == 0:
        return None

    ratio = min(ancho / img_ancho, alto / img_alto)
    sw = int(img_ancho * ratio)
    sh = int(img_alto * ratio)
    ox = (ancho - sw) // 2
    oy = (alto - sh) // 2

    x, y = event.x, event.y
    if x < ox or x > ox + sw or y < oy or y > oy + sh:
        return None

    rx = (x - ox) / sw
    ry = (y - oy) / sh
    rx = min(max(rx, 0.0), 1.0)
    ry = min(max(ry, 0.0), 1.0)
    return rx, ry


def al_presionar_click(event):
    global izq_presionado
    if not conectado:
        return "break"
    rel = coordenadas_relativas(event)
    if not rel:
        return "break"
    app.focus_force()
    if event.num == 1:
        izq_presionado = True
        enviar_al_cliente({"tipo": "control", "accion": "mouse_down", "boton": "izq", "x": rel[0], "y": rel[1]})
    elif event.num == 3:
        enviar_al_cliente({"tipo": "control", "accion": "mouse_down", "boton": "der", "x": rel[0], "y": rel[1]})
    elif event.num == 2:
        enviar_al_cliente({"tipo": "control", "accion": "mouse_down", "boton": "medio", "x": rel[0], "y": rel[1]})
    return "break"


def al_soltar_click(event):
    global izq_presionado
    if not conectado:
        return "break"
    rel = coordenadas_relativas(event)
    if not rel:
        return "break"
    if event.num == 1:
        izq_presionado = False
        enviar_al_cliente({"tipo": "control", "accion": "mouse_up", "boton": "izq", "x": rel[0], "y": rel[1]})
    elif event.num == 3:
        enviar_al_cliente({"tipo": "control", "accion": "mouse_up", "boton": "der", "x": rel[0], "y": rel[1]})
    elif event.num == 2:
        enviar_al_cliente({"tipo": "control", "accion": "mouse_up", "boton": "medio", "x": rel[0], "y": rel[1]})
    return "break"


def al_mover_mouse(event):
    global ultimo_envio_mover
    if not conectado:
        return
    rel = coordenadas_relativas(event)
    if not rel:
        return
    ahora = time.time()
    if ahora - ultimo_envio_mover < 0.01:
        return
    ultimo_envio_mover = ahora
    if izq_presionado:
        enviar_al_cliente({"tipo": "control", "accion": "arrastrar", "x": rel[0], "y": rel[1]})
    else:
        enviar_al_cliente({"tipo": "control", "accion": "mover", "x": rel[0], "y": rel[1]})


def al_rueda_mouse(event):
    if not conectado:
        return "break"
    if event.delta == 0:
        return "break"
    enviar_al_cliente({"tipo": "control", "accion": "scroll", "delta": event.delta})
    return "break"


def al_entrar_pantalla(event):
    if conectado:
        app.focus_force()
    return "break"


def tecla_m(event):
    if conectado:
        alternar_maximizado()
    return "break"


def tecla_f11(event):
    if conectado:
        alternar_maximizado()
    return "break"


def tecla_esc(event):
    if conectado and maximizado:
        alternar_maximizado()
    return "break"


def al_apretar_tecla(event):
    if not conectado:
        return "break"

    if event.state & 0x0004:
        tecla_sym = event.keysym.lower()
        if tecla_sym in ['c', 'v', 'a', 's', 'g', 'z', 'x', 'e']:
            app.after(100, sincronizar_portapapeles)
            enviar_al_cliente({"tipo": "control", "accion": "ctrl_combo", "tecla": tecla_sym})
            return "break"

    global ultimo_envio_tecla
    ultimo_envio_tecla = time.time()

    if event.char and event.char not in ('\x00', '\r', '\n', '\t', '\x08', '\x7f'):
        enviar_al_cliente({"tipo": "control", "accion": "tecla_char", "tecla": event.char})
        return "break"

    if event.keysym:
        enviar_al_cliente({"tipo": "control", "accion": "tecla", "tecla": event.keysym})
    return "break"


pantalla_label.bind("<ButtonPress-1>", al_presionar_click)
pantalla_label.bind("<ButtonRelease-1>", al_soltar_click)
pantalla_label.bind("<ButtonPress-3>", al_presionar_click)
pantalla_label.bind("<ButtonRelease-3>", al_soltar_click)
pantalla_label.bind("<ButtonPress-2>", al_presionar_click)
pantalla_label.bind("<ButtonRelease-2>", al_soltar_click)
pantalla_label.bind("<Motion>", al_mover_mouse)
pantalla_label.bind("<Configure>", redibujar_frame_actual)
pantalla_label.bind("<Enter>", al_entrar_pantalla)


async def conectar_con_codigo(codigo):
    global ws_global, loop_global, conectado, codigo_conectado, tiempo_inicio, ultimo_portapapeles
    loop_global = asyncio.get_running_loop()
    codigo_conectado = codigo
    try:
        async with websockets.connect(SERVIDOR) as ws:
            ws_global = ws
            await ws.send(json.dumps({"tipo": "unirse_con_codigo", "codigo": codigo}))
            while True:
                try:
                    respuesta = json.loads(await ws.recv())
                except websockets.exceptions.ConnectionClosed:
                    set_estado("Conexión perdida con el servidor", "#D9634F")
                    reset_estado()
                    break

                if respuesta["tipo"] == "conectado":
                    conectado = True
                    tiempo_inicio = time.time()
                    ultimo_portapapeles = pyperclip.paste()
                    habilitar_conexion(False)
                    ocultar_panel_conexion()
                    contenedor_pantalla.pack(expand=True, fill="both")
                    actualizar_tiempo()
                    sincronizar_portapapeles()
                    app.bind_all("<MouseWheel>", al_rueda_mouse)
                    app.bind_all("<KeyPress-m>", tecla_m)
                    app.bind_all("<KeyPress-M>", tecla_m)
                    app.bind_all("<KeyPress-F11>", tecla_f11)
                    app.bind_all("<KeyPress-Escape>", tecla_esc)
                    app.bind_all("<KeyPress>", al_apretar_tecla)
                    pantalla_label.bind("<MouseWheel>", al_rueda_mouse)
                    contenedor_pantalla.bind("<MouseWheel>", al_rueda_mouse)
                    app.focus_force()

                elif respuesta["tipo"] == "frame":
                    datos = base64.b64decode(respuesta["datos"])
                    imagen = Image.open(io.BytesIO(datos))
                    mostrar_frame(imagen)

                elif respuesta["tipo"] == "error":
                    set_estado(respuesta["mensaje"], "#D9634F")
                    reset_estado()
                    break

                elif respuesta["tipo"] == "sesion_cortada":
                    set_estado("Sesión cortada. Ingresá un código nuevo.", "#D9634F")
                    reset_estado()
                    break
    except Exception:
        set_estado("No se pudo conectar al servidor", "#D9634F")
        reset_estado()


def al_hacer_clic():
    codigo = entrada_codigo.get().strip().replace(" ", "")
    if len(codigo) != 6 or not codigo.isdigit():
        set_estado("Ingresá los 6 dígitos del código", "#D9634F")
        return
    set_estado("Conectando...")
    habilitar_conexion(False)

    def hilo():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(conectar_con_codigo(codigo))
        loop.close()

    threading.Thread(target=hilo, daemon=True).start()


app.mainloop()
