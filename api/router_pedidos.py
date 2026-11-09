from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

import service
from database import get_session
from models import EstadoPedido
from schemas import EstadoPatch, Pagina, PedidoCreate, PedidoRead, ResumenPedidos


router = APIRouter(prefix="/pedidos", tags=["pedidos"])
Sesion = Annotated[Session, Depends(get_session)]


@router.post("/", response_model=PedidoRead, status_code=201)
def crear_pedido(datos: PedidoCreate, session: Sesion):
    return service.crear_pedido(session, datos)


@router.get("/", response_model=Pagina[PedidoRead])
def listar_pedidos(
    session: Sesion,
    estado: EstadoPedido | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    return service.listar_pedidos(session, estado, skip, limit)


@router.get("/resumen", response_model=ResumenPedidos)
def resumir_pedidos(session: Sesion):
    return service.resumir_pedidos(session)


@router.get("/{pedido_id}", response_model=PedidoRead)
def obtener_pedido(pedido_id: int, session: Sesion):
    return service.obtener_pedido(session, pedido_id)


@router.patch("/{pedido_id}/estado", response_model=PedidoRead)
def cambiar_estado(pedido_id: int, datos: EstadoPatch, session: Sesion):
    return service.cambiar_estado(session, pedido_id, datos.estado)
