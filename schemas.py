from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models import EstadoPedido, FormaPago


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategoriaCreate(Schema):
    nombre: str = Field(min_length=2, max_length=50)
    descripcion: str = Field(default="", max_length=200)


class CategoriaRead(CategoriaCreate):
    id: int
    activo: bool


class EtiquetaCreate(Schema):
    nombre: str = Field(min_length=2, max_length=30)


class EtiquetaRead(EtiquetaCreate):
    id: int


class ProductoCreate(Schema):
    nombre: str = Field(min_length=3, max_length=60)
    descripcion: str = Field(default="", max_length=200)
    precio: float = Field(gt=0, allow_inf_nan=False)
    stock: int = Field(default=0, ge=0)
    imagen_url: str | None = Field(default=None, max_length=255)
    categoria_id: int = Field(gt=0)


class ProductoPatch(Schema):
    nombre: str | None = Field(default=None, min_length=3, max_length=60)
    descripcion: str | None = Field(default=None, max_length=200)
    precio: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    stock: int | None = Field(default=None, ge=0)
    imagen_url: str | None = Field(default=None, max_length=255)
    categoria_id: int | None = Field(default=None, gt=0)

    @field_validator("nombre", "descripcion", "precio", "stock", "categoria_id")
    @classmethod
    def rechazar_nulos(cls, valor):
        if valor is None:
            raise ValueError("El campo no puede ser nulo")
        return valor


class ProductoResumen(ProductoCreate):
    id: int
    activo: bool


class CategoriaDetalle(CategoriaRead):
    productos: list[ProductoResumen]


class ProductoRead(ProductoResumen):
    categoria: CategoriaRead
    etiquetas: list[EtiquetaRead]


class DetalleCreate(Schema):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(ge=1)


class PedidoBase(Schema):
    cliente_nombre: str = Field(min_length=3, max_length=80)
    direccion_entrega: str = Field(min_length=5, max_length=200)
    forma_pago: FormaPago
    notas: str | None = Field(default=None, max_length=200)


class PedidoCreate(PedidoBase):
    detalles: list[DetalleCreate] = Field(min_length=1)


class DetalleRead(DetalleCreate):
    id: int
    pedido_id: int
    nombre_producto: str
    precio_unitario: float
    subtotal: float


class PedidoRead(PedidoBase):
    id: int
    estado: EstadoPedido
    total: float
    fecha: datetime
    detalles: list[DetalleRead]


class EstadoPatch(Schema):
    estado: EstadoPedido


class ResumenPedidos(Schema):
    pendientes: int
    en_preparacion: int
    entregados: int
    cancelados: int
    ingresos_entregados: float


T = TypeVar("T")


class Pagina(Schema, Generic[T]):
    total: int
    items: list[T]
