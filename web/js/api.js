// La URL pública se completa al publicar desde GitHub Actions.
const API_PUBLICA = "";
const esLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const API_BASE = esLocal ? "http://127.0.0.1:8000" : API_PUBLICA;

export class ErrorApi extends Error {
  constructor(estado, detail) {
    super(typeof detail === "string" ? detail : "Revisá los datos del formulario.");
    this.name = "ErrorApi";
    this.estado = estado;
    this.detail = detail;
  }
}

async function solicitar(ruta, opciones = {}) {
  if (!API_BASE) {
    throw new ErrorApi(0, "Falta configurar la dirección de la API publicada. Consultá el README del proyecto.");
  }
  let respuesta;
  try {
    respuesta = await fetch(API_BASE.replace(/\/$/, "") + ruta, opciones);
  } catch (error) {
    if (error.name === "AbortError") throw new ErrorApi(0, "Solicitud cancelada.");
    throw new ErrorApi(0, "No pudimos conectar con Food Store. Verificá que la API esté encendida y reintentá.");
  }
  let datos;
  try {
    datos = await respuesta.json();
  } catch {
    throw new ErrorApi(respuesta.status, "La API devolvió una respuesta que no pudimos interpretar.");
  }
  if (!respuesta.ok) {
    throw new ErrorApi(respuesta.status, datos.detail ?? "La API rechazó la solicitud.");
  }
  return datos;
}

export function obtenerCategorias(signal) {
  return solicitar("/categorias/", { signal });
}

export function obtenerProductos({ categoriaId = "", skip = 0, limit = 10 } = {}, signal) {
  const parametros = new URLSearchParams({ skip, limit });
  if (categoriaId) parametros.set("categoria_id", categoriaId);
  return solicitar("/productos/?" + parametros, { signal });
}

export function crearProducto(datos) {
  return solicitar("/productos/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  });
}

export function obtenerProducto(id) {
  return solicitar("/productos/" + id);
}

export function actualizarProducto(id, cambios) {
  return solicitar("/productos/" + id, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cambios),
  });
}

export function darDeBajaProducto(id) {
  return solicitar("/productos/" + id, { method: "DELETE" });
}
