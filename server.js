// Servidor de señalización de ScreenSupport
const { WebSocketServer } = require("ws");

const PUERTO = process.env.PORT || 8080;
const wss = new WebSocketServer({ port: PUERTO, host: "0.0.0.0" });
const sesionesEsperando = new Map();

function generarCodigo() {
  let codigo;
  do {
    codigo = String(Math.floor(100000 + Math.random() * 900000));
  } while (sesionesEsperando.has(codigo));
  return codigo;
}

wss.on("connection", (socket) => {
  socket.on("message", (raw) => {
    try {
      const mensaje = JSON.parse(raw);

      if (mensaje.tipo === "generar_codigo") {
        const codigo = generarCodigo();
        socket.codigo = codigo;
        socket.rol = "cliente";
        sesionesEsperando.set(codigo, socket);
        socket.send(JSON.stringify({ tipo: "codigo_generado", codigo }));
        return;
      }

      if (mensaje.tipo === "unirse_con_codigo") {
        const socketCliente = sesionesEsperando.get(mensaje.codigo);
        if (!socketCliente) {
          socket.send(JSON.stringify({ tipo: "error", mensaje: "Código inválido o vencido" }));
          return;
        }
        if (socketCliente.par) {
          socket.send(JSON.stringify({ tipo: "error", mensaje: "Este código ya está en uso" }));
          return;
        }

        socket.par = socketCliente;
        socket.rol = "tecnico";
        socketCliente.par = socket;
        sesionesEsperando.delete(mensaje.codigo);

        socket.send(JSON.stringify({ tipo: "conectado", rol: "tecnico" }));
        socketCliente.send(JSON.stringify({ tipo: "conectado", rol: "cliente" }));
        return;
      }

      if (
        (mensaje.tipo === "webrtc" ||
          mensaje.tipo === "frame" ||
          mensaje.tipo === "control" ||
          mensaje.tipo === "bloquear_entrada" ||
          mensaje.tipo === "desbloquear_entrada" ||
          mensaje.tipo === "clipboard") &&
        socket.par &&
        socket.par.readyState === 1
      ) {
        socket.par.send(JSON.stringify(mensaje));
        return;
      }

      if ((mensaje.tipo === "cortar_sesion" || mensaje.tipo === "cortar") && socket.par) {
        if (socket.par.readyState === 1) {
          socket.par.send(JSON.stringify({ tipo: "sesion_cortada" }));
        }
        socket.par.par = null;
        socket.par = null;
        return;
      }
    } catch {
      return;
    }
  });

  socket.on("close", () => {
    if (socket.rol === "cliente") {
      if (socket.par && socket.par.readyState === 1) {
        socket.par.send(JSON.stringify({ tipo: "sesion_cortada" }));
        socket.par.par = null;
      }
      if (socket.codigo) sesionesEsperando.delete(socket.codigo);
      return;
    }
    if (socket.rol === "tecnico" && socket.par) {
      socket.par.par = null;
      return;
    }
    if (socket.codigo && !socket.par) sesionesEsperando.delete(socket.codigo);
  });
});

console.log(`Servidor de señalización escuchando en puerto ${PUERTO}`);
