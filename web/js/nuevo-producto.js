import { actualizarProducto, crearProducto, obtenerCategorias, obtenerProducto } from "./api.js";
import { validarProducto } from "./validaciones.js";
import { cargarOpciones } from "./ui.js";

const formulario = document.querySelector("#formulario");
const categoria = document.querySelector("#categoria_id");
const estado = document.querySelector("#estado");
const guardar = document.querySelector("#guardar");
const reintentar = document.querySelector("#reintentar");
const parametros = new URLSearchParams(window.location.search);
const editando = parametros.has("editar");
const productoId = Number(parametros.get("editar"));
const pagina = Number(parametros.get("pagina"));
const volver = new URL("productos.html", window.location.href);
const textoGuardar = editando ? "Guardar cambios" : "Crear producto";
let datosOriginales;

if (editando) {
  document.title = "Editar producto · Food Store";
  document.querySelector("#ceja-formulario").textContent = "Gestioná tu catálogo";
  document.querySelector("#titulo-formulario").textContent = "Editar producto";
  document.querySelector("#descripcion-formulario").textContent = "Actualizá los datos del producto y guardá los cambios.";
  document.querySelector('nav [href="nuevo-producto.html"]').removeAttribute("aria-current");
  document.querySelector('nav [href="productos.html"]').setAttribute("aria-current", "page");
  formulario.elements.precio.min = "0";
  if (Number.isSafeInteger(pagina) && pagina > 0) volver.searchParams.set("pagina", pagina);
  for (const enlace of document.querySelectorAll('main a[href="productos.html"]')) {
    enlace.href = volver;
  }
}
guardar.textContent = textoGuardar;

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

async function cargarFormulario() {
  guardar.disabled = true;
  categoria.disabled = true;
  reintentar.hidden = true;
  estado.hidden = false;
  estado.classList.remove("estado--error");
  estado.textContent = editando ? "Cargando producto…" : "Cargando categorías…";
  formulario.hidden = editando;
  if (editando && (!Number.isSafeInteger(productoId) || productoId <= 0)) {
    estado.textContent = "El enlace de edición del producto no es válido.";
    estado.classList.add("estado--error");
    return;
  }
  try {
    const [categorias, producto] = await Promise.all([
      obtenerCategorias(),
      editando ? obtenerProducto(productoId) : null,
    ]);
    if (producto && !producto.activo) {
      estado.textContent = "Este producto ya está dado de baja.";
      estado.classList.add("estado--error");
      return;
    }
    cargarOpciones(categoria, categorias);
    estado.hidden = categorias.length > 0;
    estado.textContent = "Todavía no hay categorías disponibles para crear productos.";
    guardar.disabled = categorias.length === 0;
    categoria.disabled = categorias.length === 0;
    if (producto) {
      for (const campo of ["nombre", "descripcion", "precio", "stock", "imagen_url", "categoria_id"]) {
        formulario.elements[campo].value = producto[campo] ?? "";
      }
      datosOriginales = leerDatos();
    }
    formulario.hidden = false;
  } catch (error) {
    estado.textContent = error.message;
    estado.classList.add("estado--error");
    reintentar.hidden = false;
  }
}

function leerDatos() {
  const valores = new FormData(formulario);
  const imagen = valores.get("imagen_url").trim();
  return {
    nombre: valores.get("nombre").trim(),
    descripcion: valores.get("descripcion"),
    precio: Number(valores.get("precio")),
    stock: Number(valores.get("stock")),
    imagen_url: imagen || null,
    categoria_id: Number(valores.get("categoria_id")),
  };
}

formulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  if (guardar.disabled) return;
  limpiarErrores();
  const datos = leerDatos();
  const cambios = editando
    ? Object.fromEntries(Object.entries(datos).filter(([campo, valor]) => valor !== datosOriginales[campo]))
    : datos;
  const errores = validarProducto(datos);
  const erroresAplicables = Object.entries(errores).filter(([campo]) => campo in cambios);
  if (erroresAplicables.length) {
    for (const [campo, mensaje] of erroresAplicables) mostrarError(campo, mensaje);
    formulario.querySelector('[aria-invalid="true"]').focus();
    return;
  }
  if (editando && Object.keys(cambios).length === 0) {
    window.location.assign(volver);
    return;
  }
  guardar.disabled = true;
  guardar.textContent = "Guardando…";
  estado.textContent = "Estamos guardando el producto…";
  estado.hidden = false;
  estado.classList.remove("estado--error");
  try {
    const producto = editando
      ? await actualizarProducto(productoId, cambios)
      : await crearProducto(datos);
    volver.searchParams.set(editando ? "actualizado" : "creado", producto.id);
    window.location.assign(volver);
  } catch (error) {
    estado.textContent = error.message;
    estado.classList.add("estado--error");
    if (error.estado === 409) mostrarError("nombre", error.detail);
    if (error.estado === 404 && "categoria_id" in cambios) mostrarError("categoria_id", error.detail);
    if (error.estado === 422 && Array.isArray(error.detail)) {
      for (const detalle of error.detail) mostrarError(detalle.loc[1], detalle.msg);
    }
    formulario.querySelector('[aria-invalid="true"]')?.focus();
  } finally {
    guardar.disabled = false;
    guardar.textContent = textoGuardar;
  }
});

reintentar.addEventListener("click", cargarFormulario);
cargarFormulario();
