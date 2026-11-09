from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session

import database
import router_categorias
import router_etiquetas
import router_pedidos
import router_productos
import service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.crear_tablas()
    with Session(database.engine) as session:
        service.cargar_datos_de_ejemplo(session)
    yield


app = FastAPI(title="Food Store API", lifespan=lifespan)


@app.exception_handler(service.NoEncontrado)
async def responder_no_encontrado(_request: Request, error: service.NoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(service.Conflicto)
async def responder_conflicto(_request: Request, error: service.Conflicto):
    return JSONResponse(status_code=409, content={"detail": str(error)})


app.include_router(router_categorias.router)
app.include_router(router_etiquetas.router)
app.include_router(router_productos.router)
app.include_router(router_pedidos.router)


@app.get("/")
def inicio():
    return {"mensaje": "Food Store API funcionando"}
