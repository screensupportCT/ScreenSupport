# ScreenSupport

Soporte remoto simple: compartí pantalla y recibí ayuda a distancia, con un código de 6 dígitos y consentimiento explícito en cada sesión.

## 🧪 ¡Probalo!

Esta app está en desarrollo activo y cualquiera puede ayudar a mejorarla. Descargá la última versión desde la pestaña **[Releases](../../releases)** de este repositorio, probala, y contame qué tal te fue.

- ¿Encontraste un error? Abrí un [Issue](../../issues).
- ¿Tenés una idea o mejora? ¡Mandá tu propio Pull Request! Toda contribución es bienvenida, desde arreglar un detalle de la interfaz hasta sumar una función nueva.

## ¿Qué incluye este repositorio?

- `server.js` — el servidor de señalización (Node.js), conecta a técnico y cliente mediante un código de 6 dígitos.
- `Cliente.py` — la app que comparte pantalla y recibe control remoto (quien pide ayuda).
- `Tecnico.py` — la app que ve y controla la pantalla remota (quien brinda soporte).

## Cómo correrlo vos mismo

1. Instalá [Node.js](https://nodejs.org) y corré `npm install ws`, después `node server.js`.
2. Instalá Python y las dependencias: `pip install customtkinter websockets mss pillow pyautogui pyperclip`.
3. Ejecutá `Cliente.py` en la PC que va a compartir pantalla, y `Tecnico.py` en la que va a ayudar.

## Principios del proyecto

- El cliente **siempre** ve un indicador de que está compartiendo pantalla, y puede cortar la sesión en cualquier momento.
- Cada código de conexión es de un solo uso.
- El servidor de señalización nunca graba ni accede al contenido de la pantalla compartida — solo reenvía los datos entre las dos apps.

---

Hecho aprendiendo a programar, un paso a la vez. 🚀
