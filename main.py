import os
import json
import pymongo
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, WebSocket, Request, HTTPException, WebSocketDisconnect

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')

mongo_client = pymongo.MongoClient('mongodb://localhost:27017/')
db = mongo_client['whatsapp_messages']
collection = db['messages']

app.mount("/static", StaticFiles(directory="static"), name="static")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket('/ws')
async def ws(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        data = [json.loads(json.dumps(document, default=str))
                for document in collection.find()]
        data = json.dumps(data)

        await manager.broadcast(data)

        while True:
            data = await websocket.receive_text()
            # await manager.send_personal_message(f"You wrote: {data}", websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get('/whatsapp-business/webhook')
def verify_facebook_webhook(request: Request):
    challenge = request.query_params.get('hub.challenge')
    verify_token = request.query_params.get('hub.verify_token')

    if not verify_token == VERIFY_TOKEN:
        raise HTTPException(
            status_code=403, detail="Invalid verification token")

    return int(challenge)


@app.post('/whatsapp-business/webhook')
async def receive_whatsapp_webhook(request: Request):
    json_data = await request.json()

    result = collection.insert_one(json_data)
    new_object = {"_id": str(result.inserted_id), **json_data}

    str_data = json.dumps(new_object, default=str)

    await manager.broadcast(str_data)


@app.get('/politica-de-privacidade', response_class=HTMLResponse)
async def politica_de_privacidade():
    return open("static/politica_de_privacidade.html").read()
