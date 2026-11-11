export const formatoPrecio = new Intl.NumberFormat("es-AR", {
  style: "currency", currency: "ARS", maximumFractionDigits: 2,
});

const fotosDeEjemplo = ["hamburguesas", "pizzas", "acompanamientos", "bebidas"];

export function elemento(etiqueta, clase, texto) {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
}

export function cargarOpciones(select, categorias) {
  // Se conserva la primera opción del HTML.
  while (select.options.length > 1) select.remove(1);
  for (const categoria of categorias) {
    const opcion = elemento("option", "", categoria.nombre);
    opcion.value = categoria.id;
    select.append(opcion);
  }
}

export function crearImagen(producto) {
  const marco = elemento("div", "tarjeta__imagen");
  const sinImagen = elemento("span", "sin-imagen", "Sin imagen");
  marco.append(sinImagen);
  if (producto.imagen_url) {
    try {
      const ruta = new URL(producto.imagen_url, document.baseURI);
      if (!["http:", "https:"].includes(ruta.protocol)) return marco;
      // Los productos de ejemplo ya guardados pueden tener la ruta de la ilustración.
      const carpeta = new URL("img/", document.baseURI);
      const foto = fotosDeEjemplo.find(nombre => ruta.origin === carpeta.origin
        && ruta.pathname === carpeta.pathname + nombre + ".svg");
      if (foto) ruta.pathname = carpeta.pathname + foto + ".webp";
      const imagen = elemento("img");
      imagen.alt = foto ? "" : producto.nombre;
      imagen.loading = "lazy";
      imagen.width = 480;
      imagen.height = 320;
      imagen.addEventListener("load", () => { sinImagen.hidden = true; });
      imagen.addEventListener("error", () => { imagen.remove(); sinImagen.hidden = false; });
      imagen.src = ruta.href;
      marco.append(imagen);
    } catch {
      return marco;
    }
  }
  return marco;
}

export function prepararPaginacion(limite, cambiar) {
  return {
    contenedor: document.querySelector("#paginacion"),
    anterior: document.querySelector("#anterior"),
    siguiente: document.querySelector("#siguiente"),
    texto: document.querySelector("#pagina"),
    limite, cambiar,
  };
}
