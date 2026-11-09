from datetime import UTC, datetime
from enum import Enum

from sqlmodel import Field, Relationship, SQLModel


class FormaPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"


class EstadoPedido(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_PREPARACION = "EN_PREPARACION"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"


class ProductoEtiqueta(SQLModel, table=True):
    producto_id: int = Field(foreign_key="producto.id", primary_key=True)
    etiqueta_id: int = Field(foreign_key="etiqueta.id", primary_key=True)


class Categoria(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=50, unique=True)
    descripcion: str = Field(default="", max_length=200)
    activo: bool = True

    productos: list["Producto"] = Relationship(
        back_populates="categoria", sa_relationship_kwargs={"order_by": "Producto.id"}
    )


class Etiqueta(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=30, unique=True)

    productos: list["Producto"] = Relationship(
        back_populates="etiquetas", link_model=ProductoEtiqueta
    )


class Producto(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=60, unique=True)
    descripcion: str = Field(default="", max_length=200)
    precio: float
    stock: int = 0
    imagen_url: str | None = Field(default=None, max_length=255)
    categoria_id: int = Field(foreign_key="categoria.id")
    activo: bool = True

    categoria: Categoria = Relationship(back_populates="productos")
    etiquetas: list[Etiqueta] = Relationship(
        back_populates="productos",
        link_model=ProductoEtiqueta,
        sa_relationship_kwargs={"order_by": "Etiqueta.id"},
    )
    detalles: list["DetallePedido"] = Relationship(back_populates="producto")


def ahora_utc() -> datetime:
    return datetime.now(UTC)


class Pedido(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cliente_nombre: str = Field(max_length=80)
    direccion_entrega: str = Field(max_length=200)
    forma_pago: FormaPago
    notas: str | None = Field(default=None, max_length=200)
    estado: EstadoPedido = EstadoPedido.PENDIENTE
    total: float
    fecha: datetime = Field(default_factory=ahora_utc)

    detalles: list["DetallePedido"] = Relationship(
        back_populates="pedido", sa_relationship_kwargs={"order_by": "DetallePedido.id"}
    )


class DetallePedido(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedido.id")
    producto_id: int = Field(foreign_key="producto.id")
    nombre_producto: str = Field(max_length=60)
    precio_unitario: float
    cantidad: int
    subtotal: float

    pedido: Pedido = Relationship(back_populates="detalles")
    producto: Producto = Relationship(back_populates="detalles")
