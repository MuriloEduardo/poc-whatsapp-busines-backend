import os
import json
import pymongo
from bson import json_util
from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import threading
import queue

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')

mongo_client = pymongo.MongoClient('mongodb://localhost:27017/')
db = mongo_client['whatsapp_messages']
collection = db['messages']

app.mount("/static", StaticFiles(directory="static"), name="static")

data_queue = queue.Queue()

# Variável global para armazenar a conexão WebSocket
websocket_connection = None


@app.websocket('/ws')
async def ws(websocket: WebSocket):
    global websocket_connection
    await websocket.accept()

    # Armazene a conexão WebSocket na variável global
    websocket_connection = websocket

    # Obtenha os dados do banco de dados imediatamente após a aceitação da conexão
    data = [json.loads(json_util.dumps(document, default=str))  # Converte ObjectId para string
            for document in collection.find()]

    # Envie os dados para o cliente WebSocket
    await websocket.send_text(json.dumps(data))

    # Aguarde mensagens do cliente WebSocket e realize qualquer ação necessária
    while True:
        received = await websocket.receive_text()
        # Faça algo com a mensagem recebida, se necessário

# Função para enviar dados para o WebSocket


def send_data_to_websocket():
    global websocket_connection
    while True:
        if websocket_connection:
            data = data_queue.get()
            websocket_connection.send_text(json.dumps(data))


# Inicialize a função em uma thread separada
websocket_thread = threading.Thread(target=send_data_to_websocket)
websocket_thread.start()


@app.get('/webhook')
async def verify_facebook_webhook(request: dict):
    if request.get('hub.verify_token') == VERIFY_TOKEN:
        return request.get('hub.challenge')
    return 'Invalid verification token', 403


@app.post('/webhook')
async def receive_whatsapp_webhook(data: dict):
    # Insira os dados no banco de dados
    collection.insert_one(data)

    # Coloque os dados na fila para serem enviados para o WebSocket
    data_queue.put(data)

    return 'OK'


@app.get('/politica-de-privacidade', response_class=HTMLResponse)
async def politica_de_privacidade():
    return open("static/politica_de_privacidade.html").read()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, port=5000)
