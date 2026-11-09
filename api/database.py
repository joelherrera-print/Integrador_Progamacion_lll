import os
import sqlite3
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine, URL
from sqlmodel import Session, SQLModel, create_engine


@event.listens_for(Engine, "connect")
def configurar_sqlite(conexion, _registro):
    if isinstance(conexion, sqlite3.Connection):
        conexion.execute("PRAGMA foreign_keys = ON")
        conexion.create_function("casefold", 1, str.casefold, deterministic=True)


ruta_base = Path(os.environ.get("FOOD_STORE_DB_PATH", Path(__file__).resolve().with_name("foodstore.db")))
ruta_base.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    URL.create("sqlite", database=str(ruta_base)),
    connect_args={"check_same_thread": False},
)


def crear_tablas():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
