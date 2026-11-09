export function crearPaginacion({ contenedor, anterior, siguiente, texto, limite, cambiar }) {
  let pagina = 0;
  let paginas = 1;
  anterior.addEventListener("click", () => {
    if (pagina > 0) cambiar(pagina - 1);
  });
  siguiente.addEventListener("click", () => {
    if (pagina + 1 < paginas) cambiar(pagina + 1);
  });

  return {
    actualizar(actual, total) {
      pagina = actual;
      paginas = Math.max(1, Math.ceil(total / limite));
      contenedor.hidden = total === 0;
      texto.textContent = "Página " + (pagina + 1) + " de " + paginas;
      anterior.disabled = pagina === 0;
      siguiente.disabled = pagina + 1 >= paginas;
    },
    bloquear(valor) {
      anterior.disabled = valor || pagina === 0;
      siguiente.disabled = valor || pagina + 1 >= paginas;
    },
    ocultar() {
      contenedor.hidden = true;
    },
  };
}
