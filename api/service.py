from contextlib import contextmanager

from sqlalchemy.orm import selectinload
from sqlmodel import Session, func, or_, select

from models import Categoria, DetallePedido, EstadoPedido, Etiqueta, Pedido, Producto, ProductoEtiqueta
from schemas import CategoriaCreate, EtiquetaCreate, PedidoCreate, ProductoCreate, ProductoPatch


class NoEncontrado(Exception):
    pass


class Conflicto(Exception):
    pass


@contextmanager
def transaccion(session: Session):
    # SQLite reserva la escritura antes de leer el stock o comprobar nombres.
    # Así dos escrituras no toman decisiones a partir del mismo estado anterior.
    try:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        yield
        session.commit()
    except Exception:
        session.rollback()
        raise


def verificar_nombre(session, modelo, nombre, excluir_id=None):
    consulta = select(modelo.id).where(func.casefold(modelo.nombre) == nombre.casefold())
    if excluir_id is not None:
        consulta = consulta.where(modelo.id != excluir_id)
    if session.exec(consulta).first() is not None:
        raise Conflicto("Ya existe un registro con ese nombre")


def listar_categorias(session: Session):
    return session.exec(select(Categoria).where(Categoria.activo.is_(True)).order_by(Categoria.id)).all()


def obtener_categoria(session: Session, categoria_id: int):
    consulta = (
        select(Categoria)
        .where(Categoria.id == categoria_id)
        .options(selectinload(Categoria.productos))
    )
    categoria = session.exec(consulta).first()
    if categoria is None:
        raise NoEncontrado("La categoría no existe")
    return categoria


def crear_categoria(session: Session, datos: CategoriaCreate):
    with transaccion(session):
        verificar_nombre(session, Categoria, datos.nombre)
        categoria = Categoria.model_validate(datos)
        session.add(categoria)
    session.refresh(categoria)
    return categoria


def actualizar_categoria(session: Session, categoria_id: int, datos: CategoriaCreate):
    with transaccion(session):
        categoria = session.get(Categoria, categoria_id)
        if categoria is None:
            raise NoEncontrado("La categoría no existe")
        verificar_nombre(session, Categoria, datos.nombre, categoria_id)
        categoria.nombre = datos.nombre
        categoria.descripcion = datos.descripcion
    session.refresh(categoria)
    return categoria


def desactivar_categoria(session: Session, categoria_id: int):
    with transaccion(session):
        categoria = session.get(Categoria, categoria_id)
        if categoria is None:
            raise NoEncontrado("La categoría no existe")
        if not categoria.activo:
            raise Conflicto("La categoría ya está dada de baja")
        activos = select(Producto.id).where(
            Producto.categoria_id == categoria_id, Producto.activo.is_(True)
        )
        if session.exec(activos).first() is not None:
            raise Conflicto("La categoría tiene productos activos")
        categoria.activo = False
    session.refresh(categoria)
    return categoria


def listar_etiquetas(session: Session):
    return session.exec(select(Etiqueta).order_by(Etiqueta.id)).all()


def crear_etiqueta(session: Session, datos: EtiquetaCreate):
    with transaccion(session):
        verificar_nombre(session, Etiqueta, datos.nombre)
        etiqueta = Etiqueta.model_validate(datos)
        session.add(etiqueta)
    session.refresh(etiqueta)
    return etiqueta


def eliminar_etiqueta(session: Session, etiqueta_id: int):
    with transaccion(session):
        etiqueta = session.get(Etiqueta, etiqueta_id)
        if etiqueta is None:
            raise NoEncontrado("La etiqueta no existe")
        usos = select(ProductoEtiqueta.producto_id).where(ProductoEtiqueta.etiqueta_id == etiqueta_id)
        if session.exec(usos).first() is not None:
            raise Conflicto("La etiqueta está asociada a un producto")
        session.delete(etiqueta)


def validar_categoria_activa(session: Session, categoria_id: int):
    categoria = session.get(Categoria, categoria_id)
    if categoria is None or not categoria.activo:
        raise NoEncontrado("La categoría no existe o está dada de baja")


def consulta_productos():
    return select(Producto).options(selectinload(Producto.categoria), selectinload(Producto.etiquetas))


def listar_productos(session: Session, q, categoria_id, etiqueta_id, solo_con_stock, skip, limit):
    filtros = [Producto.activo.is_(True)]
    if q is not None:
        termino = q.casefold()
        filtros.append(or_(
            func.instr(func.casefold(Producto.nombre), termino) > 0,
            func.instr(func.casefold(Producto.descripcion), termino) > 0,
        ))
    if categoria_id is not None:
        filtros.append(Producto.categoria_id == categoria_id)
    if etiqueta_id is not None:
        asociados = select(ProductoEtiqueta.producto_id).where(
            ProductoEtiqueta.etiqueta_id == etiqueta_id
        )
        filtros.append(Producto.id.in_(asociados))
    if solo_con_stock:
        filtros.append(Producto.stock > 0)

    total = session.exec(select(func.count()).select_from(Producto).where(*filtros)).one()
    consulta = consulta_productos().where(*filtros).order_by(Producto.id).offset(skip).limit(limit)
    return {"total": total, "items": session.exec(consulta).all()}


def obtener_producto(session: Session, producto_id: int):
    producto = session.exec(consulta_productos().where(Producto.id == producto_id)).first()
    if producto is None:
        raise NoEncontrado("El producto no existe")
    return producto


def crear_producto(session: Session, datos: ProductoCreate):
    with transaccion(session):
        validar_categoria_activa(session, datos.categoria_id)
        verificar_nombre(session, Producto, datos.nombre)
        producto = Producto.model_validate(datos)
        session.add(producto)
        session.flush()
        producto_id = producto.id
    return obtener_producto(session, producto_id)


def actualizar_producto(session: Session, producto_id: int, datos: ProductoPatch):
    with transaccion(session):
        producto = obtener_producto(session, producto_id)
        cambios = datos.model_dump(exclude_unset=True)
        if "categoria_id" in cambios:
            validar_categoria_activa(session, cambios["categoria_id"])
        if "nombre" in cambios:
            verificar_nombre(session, Producto, cambios["nombre"], producto_id)
        producto.sqlmodel_update(cambios)
    return obtener_producto(session, producto_id)


def desactivar_producto(session: Session, producto_id: int):
    with transaccion(session):
        producto = obtener_producto(session, producto_id)
        if not producto.activo:
            raise Conflicto("El producto ya está dado de baja")
        producto.activo = False
    return obtener_producto(session, producto_id)


def asociar_etiqueta(session: Session, producto_id: int, etiqueta_id: int):
    with transaccion(session):
        producto = obtener_producto(session, producto_id)
        etiqueta = session.get(Etiqueta, etiqueta_id)
        if etiqueta is None:
            raise NoEncontrado("La etiqueta no existe")
        if etiqueta in producto.etiquetas:
            raise Conflicto("El producto ya tiene esa etiqueta")
        producto.etiquetas.append(etiqueta)
    return obtener_producto(session, producto_id)


def quitar_etiqueta(session: Session, producto_id: int, etiqueta_id: int):
    with transaccion(session):
        asociacion = session.get(ProductoEtiqueta, (producto_id, etiqueta_id))
        if asociacion is None:
            raise NoEncontrado("El producto no tiene esa etiqueta")
        session.delete(asociacion)


def obtener_pedido(session: Session, pedido_id: int):
    consulta = select(Pedido).where(Pedido.id == pedido_id).options(selectinload(Pedido.detalles))
    pedido = session.exec(consulta).first()
    if pedido is None:
        raise NoEncontrado("El pedido no existe")
    return pedido


def crear_pedido(session: Session, datos: PedidoCreate):
    with transaccion(session):
        # Primero se valida el pedido entero, luego se descuenta y se guarda.
        ids = {linea.producto_id for linea in datos.detalles}
        if len(ids) != len(datos.detalles):
            raise Conflicto("El pedido contiene productos repetidos")
        productos = {
            producto.id: producto
            for producto in session.exec(select(Producto).where(Producto.id.in_(ids)))
        }
        for linea in datos.detalles:
            producto = productos.get(linea.producto_id)
            if producto is None or not producto.activo:
                raise NoEncontrado(f"El producto {linea.producto_id} no existe o está dado de baja")
            if producto.stock < linea.cantidad:
                raise Conflicto(f"Stock insuficiente para {producto.nombre}")

        pedido = Pedido(**datos.model_dump(exclude={"detalles"}), total=0)
        for linea in datos.detalles:
            producto = productos[linea.producto_id]
            subtotal = producto.precio * linea.cantidad
            pedido.detalles.append(DetallePedido(
                producto_id=linea.producto_id,
                nombre_producto=producto.nombre,
                precio_unitario=producto.precio,
                cantidad=linea.cantidad,
                subtotal=subtotal,
            ))
            producto.stock -= linea.cantidad
        pedido.total = sum(detalle.subtotal for detalle in pedido.detalles)
        session.add(pedido)
    return obtener_pedido(session, pedido.id)


def listar_pedidos(session: Session, estado, skip, limit):
    filtros = [] if estado is None else [Pedido.estado == estado]
    total = session.exec(select(func.count()).select_from(Pedido).where(*filtros)).one()
    consulta = (
        select(Pedido)
        .where(*filtros)
        .options(selectinload(Pedido.detalles))
        .order_by(Pedido.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return {"total": total, "items": session.exec(consulta).all()}


TRANSICIONES = {
    EstadoPedido.PENDIENTE: {EstadoPedido.EN_PREPARACION, EstadoPedido.CANCELADO},
    EstadoPedido.EN_PREPARACION: {EstadoPedido.ENTREGADO, EstadoPedido.CANCELADO},
    EstadoPedido.ENTREGADO: set(),
    EstadoPedido.CANCELADO: set(),
}


def cambiar_estado(session: Session, pedido_id: int, estado: EstadoPedido):
    with transaccion(session):
        pedido = obtener_pedido(session, pedido_id)
        if estado not in TRANSICIONES[pedido.estado]:
            raise Conflicto(f"No se puede pasar de {pedido.estado.value} a {estado.value}")
        if estado == EstadoPedido.CANCELADO:
            for linea in pedido.detalles:
                linea.producto.stock += linea.cantidad
        pedido.estado = estado
    return obtener_pedido(session, pedido_id)


def resumir_pedidos(session: Session):
    consulta = select(Pedido.estado, func.count(), func.sum(Pedido.total)).group_by(Pedido.estado)
    grupos = {estado: (cantidad, total) for estado, cantidad, total in session.exec(consulta)}
    entregados, ingresos = grupos.get(EstadoPedido.ENTREGADO, (0, 0.0))
    return {
        "pendientes": grupos.get(EstadoPedido.PENDIENTE, (0, 0))[0],
        "en_preparacion": grupos.get(EstadoPedido.EN_PREPARACION, (0, 0))[0],
        "entregados": entregados,
        "cancelados": grupos.get(EstadoPedido.CANCELADO, (0, 0))[0],
        "ingresos_entregados": ingresos,
    }


def cargar_datos_de_ejemplo(session: Session):
    with transaccion(session):
        tablas = (Categoria, Etiqueta, Producto, Pedido)
        if any(session.exec(select(tabla.id).limit(1)).first() is not None for tabla in tablas):
            return

        vegetariano = Etiqueta(nombre="Vegetariano")
        sin_tacc = Etiqueta(nombre="Sin TACC")
        picante = Etiqueta(nombre="Picante")
        session.add_all([vegetariano, sin_tacc, picante])

        menu = [
            ("Pizzas", "Pizzas de masa casera", "pizzas.svg", [
                ("Pizza muzzarella", "Salsa de tomate, muzzarella y albahaca", 9200, 8, [vegetariano]),
                ("Pizza fugazza", "Cebolla y orégano sobre masa a la piedra", 8900, 6, [vegetariano]),
                ("Pizza picante", "Salsa de tomate, queso y ají", 9800, 4, [picante]),
                ("Pizza napolitana", "Tomate, ajo y muzzarella", 9900, 9, [vegetariano]),
                ("Pizza cuatro quesos", "Muzzarella, azul, provolone y parmesano", 11200, 6, [vegetariano]),
                ("Pizza de rúcula", "Rúcula fresca y parmesano", 10500, 5, [vegetariano]),
                ("Pizza de champiñones", "Champiñones salteados y queso", 10800, 7, [vegetariano]),
            ]),
            ("Hamburguesas", "Hamburguesas en pan de papa", "hamburguesas.svg", [
                ("Hamburguesa doble", "Dos medallones de carne y cheddar", 8500, 15, []),
                ("Hamburguesa clásica", "Medallón de carne, lechuga y tomate", 7200, 12, []),
                ("Hamburguesa de lentejas", "Medallón de lentejas con ensalada", 7600, 6, [vegetariano]),
                ("Hamburguesa criolla", "Carne, morrón y cebolla", 8400, 8, []),
                ("Hamburguesa picante", "Carne, cheddar y ají", 8900, 5, [picante]),
                ("Hamburguesa de garbanzos", "Garbanzos, lechuga y tomate", 7800, 7, [vegetariano]),
                ("Hamburguesa triple", "Tres medallones con cheddar", 11500, 4, []),
            ]),
            ("Acompañamientos", "Porciones para compartir", "acompanamientos.svg", [
                ("Papas fritas", "Papas crocantes con sal marina", 4000, 12, [vegetariano]),
                ("Papas con cheddar", "Papas fritas con salsa de cheddar", 4600, 8, [vegetariano]),
                ("Papas bravas", "Papas fritas con salsa de ají", 4500, 0, [vegetariano, picante]),
                ("Papas rústicas", "Papas con piel y hierbas", 4200, 10, [vegetariano]),
                ("Aros de cebolla", "Aros rebozados y crocantes", 4300, 6, [vegetariano]),
                ("Bastones de queso", "Queso rebozado con salsa de tomate", 5100, 7, [vegetariano]),
                ("Papas al romero", "Papas al horno con romero", 4400, 9, [vegetariano]),
            ]),
            ("Bebidas", "Bebidas frías", "bebidas.svg", [
                ("Gaseosa 500 ml", "Gaseosa sabor cola", 2300, 20, [sin_tacc]),
                ("Limonada", "Limón exprimido y menta", 3100, 9, [sin_tacc]),
                ("Agua mineral", "Agua sin gas de 500 ml", 1800, 10, [sin_tacc]),
                ("Agua con gas", "Agua mineral con gas de 500 ml", 1800, 12, [sin_tacc]),
                ("Jugo de naranja", "Naranja exprimida", 3200, 8, [sin_tacc]),
                ("Limonada de frutos rojos", "Limón, frutilla y arándanos", 3500, 6, [sin_tacc]),
                ("Té helado", "Té negro frío con limón", 2900, 9, [sin_tacc]),
            ]),
        ]

        for nombre, descripcion, imagen, productos in menu:
            categoria = Categoria(nombre=nombre, descripcion=descripcion)
            session.add(categoria)
            for nombre_prod, descripcion_prod, precio, stock, etiquetas in productos:
                categoria.productos.append(Producto(
                    nombre=nombre_prod,
                    descripcion=descripcion_prod,
                    precio=precio,
                    stock=stock,
                    imagen_url=f"img/{imagen}",
                    etiquetas=etiquetas,
                ))
