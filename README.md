# Food Store · Trabajo Práctico Integrador

Web de Joel Herrera para Programación III. HTML, CSS y JavaScript con módulos ES, conectada a la API FastAPI/SQLModel del Parcial 2.

## Estructura

- `api/` contiene la API, sus imágenes de referencia y la autocorrección original.
- `web/` contiene el catálogo, la lista paginada y el formulario de alta.
- `web/js/api.js` concentra la URL base, todos los fetch y el manejo uniforme de errores.
- `web/js/validaciones.js` valida datos sin acceder al DOM.
- `web/js/paginacion.js` controla Anterior, Siguiente y el indicador de página.

## Ejecutar en Windows

Se necesita Python 3.11 o superior. Abrí la carpeta del proyecto en VS Code.

En la primera terminal, desde la carpeta principal:

```powershell
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r api\requirements.txt
cd api
..\venv\Scripts\python.exe -m uvicorn main:app --reload
```

La API queda en http://127.0.0.1:8000/docs. En una segunda terminal, desde la carpeta principal:

```powershell
.\venv\Scripts\python.exe -m http.server 5500 --directory web
```

Abrí http://localhost:5500. Los módulos ES se ejecutan mediante este servidor. Al arrancar con una base vacía, se cargan 28 productos activos en 4 categorías, etiquetas e imágenes locales. La base se guarda en `api/foodstore.db`.

Para usar una ubicación persistente distinta, configurá `FOOD_STORE_DB_PATH` antes de iniciar la API.

## Comprobar la API

Desde la carpeta principal:

```powershell
cd api
..\venv\Scripts\python.exe probar_api.py
..\venv\Scripts\python.exe probar_api.py --ver-base
..\venv\Scripts\python.exe probar_api.py --transaccion
```

La autocorrección general usa bases en memoria. Los otros dos comandos trabajan con la base real. El script original se conserva íntegro.

## Recorrer la web

1. El catálogo pide los productos al servidor y arma las tarjetas con textContent.
2. Cambiar la categoría realiza una nueva consulta con categoria_id.
3. La lista solicita páginas de 10 productos con skip y limit. Los controles se calculan a partir de total.
4. Nuevo producto tiene validación HTML activa, validaciones JavaScript y mensajes de la API.
5. Una creación válida lleva a la lista, muestra el ID y solicita nuevamente la última página.
6. El catálogo ofrece 12 productos por página. Para ver el producto recién creado, recorré hasta su página.
7. La imagen vacía o un recurso que falla muestran “Sin imagen”.

Los precios y el stock son datos de ejemplo. Las ilustraciones locales se reutilizan por categoría.

## Publicación en GitHub Pages y Render

GitHub Pages publica HTML, CSS y JavaScript. FastAPI se ejecuta en Render.

1. En Render, creá un Blueprint conectado a este repositorio. `render.yaml` define un servicio gratuito que ejecuta `api/main.py`.
2. Esperá a que Render termine y copiá su URL HTTPS. Comprobá `/docs` y `/productos/`.
3. En GitHub, entrá a Settings → Secrets and variables → Actions → Variables. Creá la variable de repositorio `FOOD_STORE_API_URL` con la URL HTTPS de la API, sin `/docs`.
4. En Settings → Pages, elegí GitHub Actions como origen.
5. En Actions, ejecutá “Publicar Food Store”. La acción inyecta la URL de la API y publica únicamente `web/`.
6. El sitio del repositorio se publica en https://joelherrera-print.github.io/Integrador_Progamacion_lll/.

La API permite exclusivamente http://localhost:5500, http://127.0.0.1:5500 y https://joelherrera-print.github.io mediante CORS.

### Persistencia en Render

El plan gratuito usa un sistema de archivos efímero. SQLite funciona para la demostración mientras vive la instancia, pero los productos creados pueden perderse después de un reinicio o despliegue. Para conservar los cambios entre reinicios, usá un servicio con disco persistente, montalo por ejemplo en `/var/data` y configurá `FOOD_STORE_DB_PATH=/var/data/foodstore.db`. Los discos persistentes de Render requieren un plan pago. En ejecución local, el archivo SQLite permanece en tu computadora.

## Defensa

Con la API y la web encendidas, abrí la pestaña Red del navegador. Mostrá el producto que sale del formulario, su POST y el JSON recibido, luego verificá su fila en la web y en `--ver-base`.

Probá el formulario vacío, un nombre formado por espacios y un nombre duplicado. Señalá qué capa lo rechaza. Un nombre como `<b>Prueba</b>` se presenta como texto.

Apagá la API, recargá y comprobá el mensaje y Reintentar. Volvé a encenderla y reintentá. Recorré las páginas de la tabla y el filtro del catálogo mostrando las consultas.

El código parte de la API del parcial y se completa con una web propia. Se utilizó asistencia de Codex para la implementación y verificación. La defensa debe explicar las decisiones y el funcionamiento con palabras propias.
