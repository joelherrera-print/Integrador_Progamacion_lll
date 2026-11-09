import { obtenerCategorias, obtenerProductos } from "./api.js";
import { crearPaginacion } from "./paginacion.js";
import { cargarOpciones, crearImagen, elemento, formatoPrecio, prepararPaginacion } from "./ui.js";

const filtro = document.querySelector("#categoria");
const grilla = document.querySelector("#productos");
const estado = document.querySelector("#estado");
const reintentar = document.querySelector("#reintentar");
const limite = 12;
let pagina = 0;
let categoriasListas = false;
let solicitud;
const paginacion = crearPaginacion(prepararPaginacion(limite, cargar));

function crearTarjeta(producto) {
  const tarjeta = elemento("article", "tarjeta");
  tarjeta.append(crearImagen(producto));
  const cuerpo = elemento("div", "tarjeta__cuerpo");
  cuerpo.append(elemento("p", "ceja", producto.categoria.nombre));
  cuerpo.append(elemento("h3", "tarjeta__titulo", producto.nombre));
  cuerpo.append(elemento("p", "tarjeta__descripcion", producto.descripcion));
  const pie = elemento("div", "tarjeta__pie");
  pie.append(elemento("strong", "precio", formatoPrecio.format(producto.precio)));
  pie.append(elemento("span", producto.stock ? "disponible" : "sin-stock", producto.stock ? "Disponible" : "Sin stock"));
  cuerpo.append(pie);
  tarjeta.append(cuerpo);
  return tarjeta;
}

async function cargar(nuevaPagina = pagina) {
  solicitud?.abort();
  const controlador = new AbortController();
  solicitud = controlador;
  paginacion.bloquear(true);
  estado.textContent = "Cargando la carta…";
  estado.hidden = false;
  estado.classList.remove("estado--error");
  reintentar.hidden = true;
  grilla.replaceChildren();
  try {
    if (!categoriasListas) {
      cargarOpciones(filtro, await obtenerCategorias(controlador.signal));
      categoriasListas = true;
      filtro.disabled = false;
    }
    const datos = await obtenerProductos({
      categoriaId: filtro.value, skip: nuevaPagina * limite, limit: limite,
    }, controlador.signal);
    if (controlador.signal.aborted) return;
    pagina = nuevaPagina;
    estado.textContent = datos.total === 0 ? "Todavía no hay productos en esta categoría." : datos.total + " productos para elegir";
    grilla.replaceChildren(...datos.items.map(crearTarjeta));
    paginacion.actualizar(pagina, datos.total);
  } catch (error) {
    if (controlador.signal.aborted) return;
    estado.textContent = error.message;
    estado.classList.add("estado--error");
    reintentar.hidden = false;
    paginacion.ocultar();
  } finally {
    if (!controlador.signal.aborted) paginacion.bloquear(false);
  }
}

filtro.addEventListener("change", () => cargar(0));
reintentar.addEventListener("click", () => cargar());
cargar();
