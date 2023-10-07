import os
import json
import pymongo
import requests
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, WebSocket, Request, HTTPException, WebSocketDisconnect

load_dotenv()

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_DB_URL = os.getenv('MONGO_DB_URL')
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_API_VERSION = os.getenv('WHATSAPP_API_VERSION')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')
WHATSAPP_SENDER_NUMBER = os.getenv('WHATSAPP_SENDER_NUMBER')
WHATSAPP_RECEIVER_NUMBER = os.getenv('WHATSAPP_RECEIVER_NUMBER')

mongo_client = pymongo.MongoClient(MONGO_DB_URL)
db = mongo_client['whatsapp_messages']
messages_collection = db['messages']

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
        data = []
        for document in messages_collection.find():
            document_data = json.loads(json.dumps(document, default=str))
            if "messages" in document_data:
                for message in document_data["messages"]:
                    timestamp = document["_id"].generation_time
                    timestamp_datetime = timestamp.timestamp()
                    message["timestamps"] = timestamp_datetime

            data.append(document_data)

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

    if not verify_token == WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(
            status_code=403, detail="Invalid verification token")

    return int(challenge)


@app.post('/whatsapp-business/webhook')
async def receive_whatsapp_webhook(request: Request):
    json_data = await request.json()

    result = messages_collection.insert_one(json_data)
    json_data["_id"] = str(result.inserted_id)

    str_data = json.dumps(json_data, default=str)

    await manager.broadcast(str_data)


@app.get('/politica-de-privacidade', response_class=HTMLResponse)
def politica_de_privacidade():
    return open("static/politica_de_privacidade.html").read()


@app.post('/whatsapp-business/send-message')
async def send_message(request: Request):
    json_data = await request.json()

    message = json_data.get('message')
    phone = json_data.get('phone') if json_data.get(
        'phone') else WHATSAPP_RECEIVER_NUMBER

    data = {
        "to": phone,
        "messaging_product": "whatsapp",
    }

    if not message:
        data["type"] = "template"
        data["template"] = {
            "name": "hello_world",
            "language": {"code": "en_US"}
        }
    else:
        data["type"] = "text"
        data["text"] = {
            "body": message
        }

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_SENDER_NUMBER}/messages"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {WHATSAPP_TOKEN}'
    }
    response = requests.post(url, json=data, headers=headers)
    response_json_data = response.json()

    response_json_data["messages"][0]["data"] = data

    result = messages_collection.insert_one(response_json_data)

    inserted_id = result.inserted_id
    timestamp = inserted_id.generation_time
    timestamp_datetime = timestamp.timestamp()

    response_json_data["_id"] = str(inserted_id)
    response_json_data["messages"][0]["timestamps"] = timestamp_datetime

    str_data = json.dumps(response_json_data, default=str)

    await manager.broadcast(str_data)
