import ConnectionManager
from fastapi import FastAPI
from dotenv import load_dotenv
from pymongo import MongoClient
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from services.openia import get_openai_response
from dependencies import get_manager, get_mongo
from routes import whatsapp_routes, openai_routes
from fastapi.middleware.cors import CORSMiddleware
from services.whatsapp import mount_whatsapp_messages
from fastapi import Depends, WebSocket, WebSocketDisconnect

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(whatsapp_routes.router,
                   prefix="/whatsapp-business", tags=["whatsapp"])

app.include_router(openai_routes.router, prefix="/openai", tags=["openai"])


@app.get('/politica-de-privacidade', response_class=HTMLResponse)
def politica_de_privacidade():
    return open("static/politica_de_privacidade.html").read()


@app.websocket('/ws')
async def ws(websocket: WebSocket, manager: ConnectionManager = Depends(get_manager), mongo: MongoClient = Depends(get_mongo)):
    try:
        await manager.connect(websocket)

        whatsapp_messages = mongo['whatsapp_messages']
        messages_collection = whatsapp_messages['messages']
        messages = messages_collection.find()
        messages = mount_whatsapp_messages(messages)

        await manager.send_personal_message({
            "type": "whatsapp",
            "data": messages
        }, websocket)

        while True:
            data = await websocket.receive_text()

            if data == "openai":
                response = get_openai_response(data)

                await manager.send_personal_message({
                    "type": "openai",
                    "data": response
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
