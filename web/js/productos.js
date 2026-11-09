import { obtenerProductos } from "./api.js";
import { crearPaginacion } from "./paginacion.js";
import { elemento, formatoPrecio, prepararPaginacion } from "./ui.js";

const filas = document.querySelector("#filas");
const estado = document.querySelector("#estado");
const total = document.querySelector("#total");
const reintentar = document.querySelector("#reintentar");
const creado = Number(new URLSearchParams(window.location.search).get("creado"));
const limite = 10;
let pagina = 0;
let irAlUltimo = Number.isInteger(creado) && creado > 0;
let solicitud;
const paginacion = crearPaginacion(prepararPaginacion(limite, cargar));

if (irAlUltimo) {
  const exito = document.querySelector("#exito");
  exito.textContent = "Producto #" + creado + " creado. La lista se actualizó desde la API.";
  exito.hidden = false;
}

function crearFila(producto) {
  const fila = elemento("tr");
  for (const dato of [producto.id, producto.nombre, producto.categoria.nombre, formatoPrecio.format(producto.precio)]) {
    fila.append(elemento("td", "", dato));
  }
  const stock = elemento("td");
  stock.append(elemento("span", producto.stock ? "disponible" : "sin-stock", producto.stock ? producto.stock + " unidades" : "Sin stock"));
  fila.append(stock);
  return fila;
}

async function cargar(nuevaPagina = pagina) {
  solicitud?.abort();
  const controlador = new AbortController();
  solicitud = controlador;
  estado.textContent = "Cargando productos…";
  estado.hidden = false;
  estado.classList.remove("estado--error");
  reintentar.hidden = true;
  paginacion.bloquear(true);
  filas.replaceChildren();
  try {
    let datos = await obtenerProductos({ skip: nuevaPagina * limite, limit: limite }, controlador.signal);
    if (irAlUltimo) {
      nuevaPagina = Math.max(0, Math.ceil(datos.total / limite) - 1);
      datos = await obtenerProductos({ skip: nuevaPagina * limite, limit: limite }, controlador.signal);
      irAlUltimo = false;
    }
    if (controlador.signal.aborted) return;
    pagina = nuevaPagina;
    filas.replaceChildren(...datos.items.map(crearFila));
    total.textContent = datos.total + " productos";
    estado.textContent = "Todavía no hay productos. Agregá el primero desde el formulario.";
    estado.hidden = datos.total > 0;
    paginacion.actualizar(pagina, datos.total);
  } catch (error) {
    if (controlador.signal.aborted) return;
    estado.textContent = error.message;
    estado.classList.add("estado--error");
    total.textContent = "";
    reintentar.hidden = false;
    paginacion.ocultar();
  } finally {
    if (!controlador.signal.aborted) paginacion.bloquear(false);
  }
}

reintentar.addEventListener("click", () => cargar());
cargar();
