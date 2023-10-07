import os
import json
import requests
from pymongo import MongoClient
from ConnectionManager import ConnectionManager
from dependencies import get_manager, get_mongo
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Request, HTTPException

WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_API_VERSION = os.getenv('WHATSAPP_API_VERSION')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')
WHATSAPP_SENDER_NUMBER = os.getenv('WHATSAPP_SENDER_NUMBER')
WHATSAPP_RECEIVER_NUMBER = os.getenv('WHATSAPP_RECEIVER_NUMBER')

router = APIRouter()


@router.get('/webhook')
def verify_facebook_webhook(request: Request):
    challenge = request.query_params.get('hub.challenge')
    verify_token = request.query_params.get('hub.verify_token')

    if not verify_token == WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(
            status_code=403, detail="Invalid verification token")

    return int(challenge)


@router.post('/webhook')
async def receive_whatsapp_webhook(
    request: Request,
    mongo_client: MongoClient = Depends(get_mongo),
    manager: ConnectionManager = Depends(get_manager)
):
    whatsapp_messages = mongo_client['whatsapp_messages']
    messages_collection = whatsapp_messages['messages']

    json_data = await request.json()

    result = messages_collection.insert_one(json_data)
    json_data["_id"] = str(result.inserted_id)

    str_data = json.dumps(json_data, default=str)

    await manager.broadcast(str_data)


@router.post('/send-message')
async def send_message(
    request: Request,
    mongo_client=Depends(get_mongo),
    manager=Depends(get_manager)
):
    whatsapp_messages = mongo_client['whatsapp_messages']
    messages_collection = whatsapp_messages['messages']

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


@router.websocket('/ws')
async def ws(
    websocket: WebSocket,
    mongo_client: MongoClient = Depends(get_mongo),
    manager: ConnectionManager = Depends(get_manager)
):
    whatsapp_messages = mongo_client['whatsapp_messages']
    messages_collection = whatsapp_messages['messages']

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
