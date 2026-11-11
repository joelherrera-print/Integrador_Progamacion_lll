import { darDeBajaProducto, obtenerProductos } from "./api.js";
import { crearPaginacion } from "./paginacion.js";
import { elemento, formatoPrecio, prepararPaginacion } from "./ui.js";

const filas = document.querySelector("#filas");
const estado = document.querySelector("#estado");
const total = document.querySelector("#total");
const reintentar = document.querySelector("#reintentar");
const exito = document.querySelector("#exito");
const dialogoBaja = document.querySelector("#dialogo-baja");
const detalleBaja = document.querySelector("#detalle-baja");
const errorBaja = document.querySelector("#error-baja");
const cancelarBaja = document.querySelector("#cancelar-baja");
const confirmarBaja = document.querySelector("#confirmar-baja");
const parametros = new URLSearchParams(window.location.search);
const creado = Number(parametros.get("creado"));
const actualizado = Number(parametros.get("actualizado"));
const paginaSolicitada = Number(parametros.get("pagina"));
const limite = 10;
let pagina = Number.isSafeInteger(paginaSolicitada) && paginaSolicitada > 0 ? paginaSolicitada - 1 : 0;
let irAlUltimo = Number.isSafeInteger(creado) && creado > 0;
let solicitud;
let productoParaBaja;
const paginacion = crearPaginacion(prepararPaginacion(limite, cargar));

if (irAlUltimo) {
  mostrarExito("Producto #" + creado + " creado. La lista se actualizó desde la API.");
} else if (Number.isSafeInteger(actualizado) && actualizado > 0) {
  mostrarExito("Guardaste los cambios del producto #" + actualizado + ".");
}

function mostrarExito(mensaje) {
  exito.textContent = mensaje;
  exito.hidden = false;
}

function pedirBaja(producto) {
  productoParaBaja = producto;
  detalleBaja.textContent = "¿Dar de baja “" + producto.nombre + "”? Dejará de aparecer en el catálogo.";
  errorBaja.hidden = true;
  dialogoBaja.showModal();
}

function crearCelda(clase, texto, etiqueta) {
  const celda = elemento("td", clase, texto);
  celda.setAttribute("role", "cell");
  if (etiqueta) {
    const rotulo = elemento("span", "etiqueta-dato", etiqueta);
    rotulo.setAttribute("aria-hidden", "true");
    celda.prepend(rotulo);
  }
  return celda;
}

function crearFila(producto) {
  const fila = elemento("tr");
  fila.setAttribute("role", "row");
  fila.append(
    crearCelda("producto-id", producto.id, "ID"),
    crearCelda("producto-nombre", producto.nombre),
    crearCelda("producto-categoria", producto.categoria.nombre, "Categoría"),
    crearCelda("producto-precio", formatoPrecio.format(producto.precio), "Precio"),
  );
  const stock = crearCelda("producto-stock", undefined, "Stock");
  stock.append(elemento("span", producto.stock ? "disponible" : "sin-stock", producto.stock ? producto.stock + " unidades" : "Sin stock"));

  const acciones = crearCelda("producto-acciones");
  const botones = elemento("div", "acciones-producto");
  const editar = elemento("a", "boton boton--secundario", "Editar");
  editar.href = "nuevo-producto.html?" + new URLSearchParams({ editar: producto.id, pagina: pagina + 1 });
  editar.setAttribute("aria-label", "Editar " + producto.nombre);
  const baja = elemento("button", "boton boton--peligro", "Dar de baja");
  baja.type = "button";
  baja.setAttribute("aria-label", "Dar de baja " + producto.nombre);
  baja.addEventListener("click", () => pedirBaja(producto));
  botones.append(editar, baja);
  acciones.append(botones);
  fila.append(stock, acciones);
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
    const ultimaPagina = Math.max(0, Math.ceil(datos.total / limite) - 1);
    if (irAlUltimo || nuevaPagina > ultimaPagina) {
      if (nuevaPagina !== ultimaPagina) {
        datos = await obtenerProductos({ skip: ultimaPagina * limite, limit: limite }, controlador.signal);
      }
      nuevaPagina = ultimaPagina;
    }
    if (controlador.signal.aborted) return;
    irAlUltimo = false;
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

dialogoBaja.addEventListener("cancel", (evento) => {
  if (confirmarBaja.disabled) evento.preventDefault();
});

confirmarBaja.addEventListener("click", async () => {
  const producto = productoParaBaja;
  confirmarBaja.disabled = true;
  cancelarBaja.disabled = true;
  confirmarBaja.textContent = "Dando de baja…";
  errorBaja.hidden = true;
  try {
    await darDeBajaProducto(producto.id);
  } catch (error) {
    if (error.estado !== 404 && error.estado !== 409) {
      errorBaja.textContent = error.message;
      errorBaja.hidden = false;
      return;
    }
  } finally {
    confirmarBaja.disabled = false;
    cancelarBaja.disabled = false;
    confirmarBaja.textContent = "Dar de baja";
  }
  dialogoBaja.close();
  mostrarExito("“" + producto.nombre + "” quedó fuera del catálogo.");
  await cargar();
  document.querySelector("#titulo-lista").focus({ preventScroll: true });
});

reintentar.addEventListener("click", () => cargar());
cargar();
