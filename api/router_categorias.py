from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

import service
from database import get_session
from schemas import CategoriaCreate, CategoriaDetalle, CategoriaRead


router = APIRouter(prefix="/categorias", tags=["categorias"])
Sesion = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=list[CategoriaRead])
def listar_categorias(session: Sesion):
    return service.listar_categorias(session)


@router.get("/{categoria_id}", response_model=CategoriaDetalle)
def obtener_categoria(categoria_id: int, session: Sesion):
    return service.obtener_categoria(session, categoria_id)


@router.post("/", response_model=CategoriaRead, status_code=201)
def crear_categoria(datos: CategoriaCreate, session: Sesion):
    return service.crear_categoria(session, datos)


@router.put("/{categoria_id}", response_model=CategoriaRead)
def actualizar_categoria(categoria_id: int, datos: CategoriaCreate, session: Sesion):
    return service.actualizar_categoria(session, categoria_id, datos)


@router.delete("/{categoria_id}", response_model=CategoriaRead)
def desactivar_categoria(categoria_id: int, session: Sesion):
    return service.desactivar_categoria(session, categoria_id)
