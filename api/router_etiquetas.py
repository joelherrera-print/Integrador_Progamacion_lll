from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

import service
from database import get_session
from schemas import EtiquetaCreate, EtiquetaRead


router = APIRouter(prefix="/etiquetas", tags=["etiquetas"])
Sesion = Annotated[Session, Depends(get_session)]


@router.get("/", response_model=list[EtiquetaRead])
def listar_etiquetas(session: Sesion):
    return service.listar_etiquetas(session)


@router.post("/", response_model=EtiquetaRead, status_code=201)
def crear_etiqueta(datos: EtiquetaCreate, session: Sesion):
    return service.crear_etiqueta(session, datos)


@router.delete("/{etiqueta_id}", status_code=204)
def eliminar_etiqueta(etiqueta_id: int, session: Sesion):
    service.eliminar_etiqueta(session, etiqueta_id)
    return Response(status_code=204)
