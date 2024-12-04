import time
import boto3
import json
from sqlalchemy.orm import sessionmaker
# from sqlalchemy import insert, update
from sqlalchemy.dialects.mysql import insert
from app.models.database import SessionLocal
from app.models.tables import pedido, produto_pedido

# Inicializar cliente SQS
sqs = boto3.client('sqs', 
                   endpoint_url='http://localstack:4566', 
                   region_name='us-east-1',
                   aws_access_key_id='LKIAQAAAAAAAKWL2ASHI',
                   aws_secret_access_key='n327Qep6xt5SkDnWV8Lf7Ywb5U6C1B1rwtzoojba')

def send_to_sqs(queue_name: str, message_body: str):
    try:
        # Get the URL for the queue
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        
        # Send the message
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body
        )
    except Exception as e:
        print(f"Error sending message to SQS: {e}")

# Receber mensagens
queues = {
    "pedido-atualizacao": "http://localstack:4566/000000000000/pedido-atualizacao"
}

def handle_sqs_message(queue_name, queue_url):
    while True:
        try:
            messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
            
            if 'Messages' in messages:
                for message in messages['Messages']:                    
                    # Processa a mensagem
                    process_message(message, queue_name)
                    # Deleta a mensagem da fila em caso de sucesso
                    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message['ReceiptHandle'])
            
            # Aguarda 5 segundos para a próxima obtenção de mensagens
            time.sleep(5)
        
        except Exception as e:
            print(f"Error processing message for queue {queue_name}: {str(e)}")
            time.sleep(10)


def process_message(message, queue_name):
    data = json.loads(message['Body'])  # Carregar o JSON da mensagem
    session = SessionLocal()
    try:
        if queue_name == "pedido-atualizacao":
            produtos_data = data.get('produtos', [])
            pedido_id = data.get('pedido_id')

            if not produtos_data or not pedido_id:
                raise ValueError("JSON inválido: 'produtos' ou 'produto_id' ausente.")

            # Inserir ou atualizar o pedido
            stmt_pedido = insert(pedido).values(
                id=pedido_id,
                status="Recebido"  # Status inicial como "Recebido"
            ).on_duplicate_key_update(
                status=pedido.c.status
            )
            session.execute(stmt_pedido)

            # Inserir ou atualizar os produtos relacionados ao pedido
            for produto_data in produtos_data:
                stmt_produto_pedido = insert(produto_pedido).values(
                    produto=produto_data.get('produto'),
                    quantidade=produto_data.get('quantidade', 0),
                    descricao=produto_data.get('descricao', ""),
                    pedido_id=pedido_id
                ).on_duplicate_key_update(
                    quantidade=produto_pedido.c.quantidade,
                    descricao=produto_pedido.c.descricao
                )
                session.execute(stmt_produto_pedido)

            session.commit()

    except Exception as e:
        session.rollback()
        print(f"Erro ao processar mensagem: {e}")
        raise
    finally:
        session.close()