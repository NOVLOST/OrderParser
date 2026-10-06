from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import storage

app = FastAPI(title="OrderParser", version="0.0.1")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):

    storage.load_orders()                          # список
storage.get_order(1)                           # Order | None
storage.add_order(                             # создаёт и возвращает Order
    origin="Ульяновск",
    destination="Москва",
    cargo="Мебель",
    price=45000,
)
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "OrderParser",
            "description": "Платформа для сбора заказов на грузоперевозки с розничных площадок",
            "version": "0.0.1",
        },
    )
