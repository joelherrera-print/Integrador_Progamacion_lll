from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

import service
from database import get_session
from schemas import Pagina, ProductoCreate, ProductoPatch, ProductoRead


router = APIRouter(prefix="/productos", tags=["productos"])
Sesion = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=Pagina[ProductoRead])
def listar_productos(
    session: Sesion,
    q: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    categoria_id: Annotated[int | None, Query(gt=0)] = None,
    etiqueta_id: Annotated[int | None, Query(gt=0)] = None,
    solo_con_stock: bool = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    return service.listar_productos(session, q, categoria_id, etiqueta_id, solo_con_stock, skip, limit)


@router.get("/{producto_id}", response_model=ProductoRead)
def obtener_producto(producto_id: int, session: Sesion):
    return service.obtener_producto(session, producto_id)


@router.post("/", response_model=ProductoRead, status_code=201)
def crear_producto(datos: ProductoCreate, session: Sesion):
    return service.crear_producto(session, datos)


@router.patch("/{producto_id}", response_model=ProductoRead)
def actualizar_producto(producto_id: int, datos: ProductoPatch, session: Sesion):
    return service.actualizar_producto(session, producto_id, datos)


@router.delete("/{producto_id}", response_model=ProductoRead)
def desactivar_producto(producto_id: int, session: Sesion):
    return service.desactivar_producto(session, producto_id)


@router.post("/{producto_id}/etiquetas/{etiqueta_id}", response_model=ProductoRead, status_code=201)
def asociar_etiqueta(producto_id: int, etiqueta_id: int, session: Sesion):
    return service.asociar_etiqueta(session, producto_id, etiqueta_id)


@router.delete("/{producto_id}/etiquetas/{etiqueta_id}", status_code=204)
def quitar_etiqueta(producto_id: int, etiqueta_id: int, session: Sesion):
    service.quitar_etiqueta(session, producto_id, etiqueta_id)
    return Response(status_code=204)
