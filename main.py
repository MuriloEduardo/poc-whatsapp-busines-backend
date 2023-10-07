from fastapi import FastAPI
from routes import whatsapp_routes
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(whatsapp_routes.router,
                   prefix="/whatsapp-business", tags=["whatsapp"])


@app.get('/politica-de-privacidade', response_class=HTMLResponse)
def politica_de_privacidade():
    return open("static/politica_de_privacidade.html").read()
