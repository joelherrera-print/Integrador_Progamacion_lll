// Reglas puras del formulario. Este módulo no accede al documento.
export function validarProducto(datos) {
  const errores = {};
  const nombre = datos.nombre.trim();
  if (nombre.length < 3 || nombre.length > 60) {
    errores.nombre = "Escribí un nombre de entre 3 y 60 caracteres, con contenido.";
  }
  if (datos.descripcion.length > 200) errores.descripcion = "Usá hasta 200 caracteres.";
  if (!Number.isFinite(datos.precio) || datos.precio <= 0) errores.precio = "El precio debe ser mayor que cero.";
  if (!Number.isInteger(datos.stock) || datos.stock < 0) errores.stock = "El stock debe ser un entero desde cero.";
  if (!Number.isInteger(datos.categoria_id) || datos.categoria_id <= 0) errores.categoria_id = "Elegí una categoría.";
  if (datos.imagen_url !== null && datos.imagen_url.length > 255) errores.imagen_url = "Usá hasta 255 caracteres.";
  return errores;
}
