from pydantic import BaseModel, field_validator
from typing import List

# Modelos Pydantic
class ProdutoItem(BaseModel):
    produto: str
    quantidade: int
    descricao: str

class Pedido(BaseModel):
    id: int = None
    status: str = "Recebido"
    produtos: List[ProdutoItem]
    