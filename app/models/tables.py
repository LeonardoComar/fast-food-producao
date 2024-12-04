from sqlalchemy import Table, Column, String, Float, Integer, Boolean, TIMESTAMP, ForeignKey, func
from .database import metadata

# Criar tabelas
pedido = Table(
    'pedido', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('status', String(50), default="Recebido"),
    Column('created_at', TIMESTAMP, server_default=func.now()),
    Column('updated_at', TIMESTAMP, server_default=func.now(), onupdate=func.now()),
)

produto_pedido = Table(
    'produto_pedido', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('produto', String(255), nullable=False),
    Column('quantidade', Integer, nullable=False),
    Column('descricao', String(255)),
    Column('pedido_id', Integer, ForeignKey('pedido.id')),
    Column('created_at', TIMESTAMP, server_default=func.now()),
    Column('updated_at', TIMESTAMP, server_default=func.now(), onupdate=func.now()),
)