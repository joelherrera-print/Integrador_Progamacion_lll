import { crearProducto, obtenerCategorias } from "./api.js";
import { validarProducto } from "./validaciones.js";
import { cargarOpciones } from "./ui.js";

const formulario = document.querySelector("#formulario");
const categoria = document.querySelector("#categoria_id");
const estado = document.querySelector("#estado");
const guardar = document.querySelector("#guardar");
const reintentar = document.querySelector("#reintentar");

function mostrarError(campo, mensaje) {
  const input = formulario.elements.namedItem(campo);
  if (!input) return;
  input.setAttribute("aria-invalid", "true");
  document.querySelector("#error-" + campo).textContent = mensaje;
}

function limpiarErrores() {
  for (const campo of formulario.elements) campo.removeAttribute("aria-invalid");
  for (const mensaje of formulario.querySelectorAll(".error-campo")) mensaje.textContent = "";
}

async function cargarCategorias() {
  guardar.disabled = true;
  categoria.disabled = true;
  reintentar.hidden = true;
  estado.hidden = false;
  estado.classList.remove("estado--error");
  estado.textContent = "Cargando categorías…";
  try {
    const categorias = await obtenerCategorias();
    cargarOpciones(categoria, categorias);
    estado.hidden = categorias.length > 0;
    estado.textContent = "Todavía no hay categorías disponibles para crear productos.";
    guardar.disabled = categorias.length === 0;
    categoria.disabled = categorias.length === 0;
  } catch (error) {
    estado.textContent = error.message;
    estado.classList.add("estado--error");
    reintentar.hidden = false;
  }
}

formulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  limpiarErrores();
  const valores = new FormData(formulario);
  const imagen = valores.get("imagen_url").trim();
  const datos = {
    nombre: valores.get("nombre"),
    descripcion: valores.get("descripcion"),
    precio: Number(valores.get("precio")),
    stock: Number(valores.get("stock")),
    imagen_url: imagen || null,
    categoria_id: Number(valores.get("categoria_id")),
  };
  const errores = validarProducto(datos);
  if (Object.keys(errores).length) {
    for (const [campo, mensaje] of Object.entries(errores)) mostrarError(campo, mensaje);
    formulario.querySelector('[aria-invalid="true"]').focus();
    return;
  }
  datos.nombre = datos.nombre.trim();
  guardar.disabled = true;
  guardar.textContent = "Guardando…";
  estado.textContent = "Estamos guardando el producto…";
  estado.hidden = false;
  estado.classList.remove("estado--error");
  try {
    const producto = await crearProducto(datos);
    window.location.assign("productos.html?creado=" + encodeURIComponent(producto.id));
  } catch (error) {
    estado.textContent = error.message;
    estado.classList.add("estado--error");
    if (error.estado === 409) mostrarError("nombre", error.detail);
    if (error.estado === 404) mostrarError("categoria_id", error.detail);
    if (error.estado === 422 && Array.isArray(error.detail)) {
      for (const detalle of error.detail) mostrarError(detalle.loc[1], detalle.msg);
    }
    formulario.querySelector('[aria-invalid="true"]')?.focus();
  } finally {
    guardar.disabled = false;
    guardar.textContent = "Crear producto";
  }
});

reintentar.addEventListener("click", cargarCategorias);
cargarCategorias();
