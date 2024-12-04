from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, update
from app.models.database import SessionLocal
from app.models.tables import pedido, produto_pedido
from app.models.schemas import Pedido
from sqlalchemy.orm import sessionmaker, Session
import json
import requests
from app.controllers.sqs import send_to_sqs

router = APIRouter()

SQS_UPDATE_QUEUE = "producao-atualizacao"

# Helper function to get session
def get_db():
    db = SessionLocal()  # Usando SessionLocal para obter a sessão
    try:
        yield db
    finally:
        db.close()

# Endpoint para listar pedidos com status "Recebido", "Em preparação", "Pronto"
@router.get("/pedidos")
def listar_pedidos(db: Session = Depends(get_db)):
    status_validos = ["Recebido", "Em preparação", "Pronto"]
    query = select(pedido).where(pedido.c.status.in_(status_validos))
    pedidos = db.execute(query).fetchall()
    
    if not pedidos:
        raise HTTPException(status_code=404, detail="Nenhum pedido encontrado")

    pedidos_list = []
    for pedido_item in pedidos:
        query_produtos = select(produto_pedido).where(produto_pedido.c.pedido_id == pedido_item.id)
        produtos = db.execute(query_produtos).fetchall()

        produtos_list = [
            {"produto": produto.produto, "quantidade": produto.quantidade, "descricao": produto.descricao}
            for produto in produtos
        ]
        
        pedidos_list.append({
            "id": pedido_item.id,
            "status": pedido_item.status,
            "produtos": produtos_list
        })
    
    return pedidos_list


# Endpoint para avançar o status do pedido
@router.put("/pedido/{pedido_id}/avancar-status")
def avancar_status(pedido_id: int, db: Session = Depends(get_db)):
    status_transicoes = {
        "Recebido": "Em preparação",
        "Em preparação": "Pronto",
        "Pronto": "Pronto",  # Não avança além de "Pronto"
    }

    # Consulta o status atual do pedido
    query = select(pedido).where(pedido.c.id == pedido_id)
    pedido_result = db.execute(query).fetchone()

    if not pedido_result:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    # Atualiza o status para a próxima etapa
    novo_status = status_transicoes.get(pedido_result.status)
    
    if novo_status is None:
        raise HTTPException(status_code=400, detail="Status do pedido já está em 'Pronto'")
    
    update_query = update(pedido).where(pedido.c.id == pedido_id).values(status=novo_status)
    db.execute(update_query)
    db.commit()

    # Enviar a mensagem para o SQS com o id do pedido e o novo status
    mensagem = {
        "pedido_id": pedido_id,
        "novo_status": novo_status
    }

    send_to_sqs(SQS_UPDATE_QUEUE, json.dumps(mensagem))
    
    return {"message": f"Status do pedido {pedido_id} alterado para '{novo_status}'"}

# Endpoint para retornar o status do pedido para etapa anterior
@router.put("/pedido/{pedido_id}/retornar-status")
def retornar_status(pedido_id: int, db: Session = Depends(get_db)):
    status_transicoes_invertidas = {
        "Pronto": "Em preparação",
        "Em preparação": "Recebido",
        "Recebido": "Recebido",  # Não volta além de "Recebido"
    }

    # Consulta o status atual do pedido
    query = select(pedido).where(pedido.c.id == pedido_id)
    pedido_result = db.execute(query).fetchone()

    if not pedido_result:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    # Atualiza o status para a etapa anterior
    novo_status = status_transicoes_invertidas.get(pedido_result.status)
    
    if novo_status is None:
        raise HTTPException(status_code=400, detail="Status do pedido já está em 'Recebido'")
    
    update_query = update(pedido).where(pedido.c.id == pedido_id).values(status=novo_status)
    db.execute(update_query)
    db.commit()

    # Enviar a mensagem para o SQS com o id do pedido e o novo status
    mensagem = {
        "pedido_id": pedido_id,
        "novo_status": novo_status
    }

    send_to_sqs(SQS_UPDATE_QUEUE, json.dumps(mensagem))
    
    return {"message": f"Status do pedido {pedido_id} alterado para '{novo_status}'"}