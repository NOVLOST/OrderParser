"""Точка входа приложения OrderParser.

Здесь только маршруты и рендеринг шаблонов.
Бизнес-логика — в actions.py, работа с БД — в storage.py.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from actions import (
    check_source_access,
    create_order,
    get_order_card,
    list_orders,
    list_sources,
)
from storage import init_schema


# ---------- приложение и шаблоны ----------

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="OrderParser", version="0.0.3")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# ---------- старт приложения ----------

@app.on_event("startup")
def on_startup() -> None:
    """Создаёт таблицы и заполняет справочник площадок.

    Выполняется один раз при старте. Повторные запуски безопасны:
    CREATE TABLE IF NOT EXISTS и ON CONFLICT DO NOTHING ничего не ломают.
    """
    init_schema()


# ---------- главная ----------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "version": "0.0.3",
        },
    )


# ---------- просмотр списка ----------

@app.get("/orders", response_class=HTMLResponse)
def orders_list(request: Request, source: str | None = None):
    """Список заказов. Параметр source — id площадки из строки фильтра."""

    source_id: int | None = None
    if source:
        try:
            source_id = int(source)
        except ValueError:
            source_id = None

    orders = list_orders(source_id=source_id)
    sources = list_sources()

    return templates.TemplateResponse(
        "orders.html",
        {
            "request": request,
            "orders": orders,
            "sources": sources,
            "selected_source": source_id,
            "version": "0.0.3",
        },
    )


# ---------- форма создания (GET) ----------

@app.get("/orders/new", response_class=HTMLResponse)
def order_new_form(request: Request):
    return templates.TemplateResponse(
        "order_form.html",
        {
            "request": request,
            "sources": list_sources(),
            "form": {},
            "error": "",
            "version": "0.0.3",
        },
    )


# ---------- форма создания (POST) ----------

@app.post("/orders/new", response_class=HTMLResponse)
def order_new_submit(
    request: Request,
    where_from: str = Form(""),
    where_to: str = Form(""),
    cargo: str = Form(""),
    price: str = Form(""),
    source_place: str = Form(""),
):
    result = create_order(
        where_from=where_from,
        where_to=where_to,
        cargo=cargo,
        price=price,
        source_place=source_place,
    )

    if not result.ok:
        # Возвращаем форму с тем же вводом и текстом ошибки.
        return templates.TemplateResponse(
            "order_form.html",
            {
                "request": request,
                "sources": list_sources(),
                "form": {
                    "where_from": where_from,
                    "where_to": where_to,
                    "cargo": cargo,
                    "price": price,
                    "source_place": source_place,
                },
                "error": result.message,
                "version": "0.0.3",
            },
            status_code=400,
        )

    # После успеха — на список, чтобы новая запись была видна.
    return RedirectResponse(url="/orders", status_code=303)


# ---------- карточка одной записи ----------

@app.get("/orders/{order_id}", response_class=HTMLResponse)
def order_detail(request: Request, order_id: int):
    result = get_order_card(order_id)
    if not result.ok:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": "Заказ не найден",
                "message": result.message,
                "version": "0.0.3",
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        "order_detail.html",
        {
            "request": request,
            "order": result.payload,
            "version": "0.0.3",
        },
    )


# ---------- проверка доступа к площадке (ошибочный сценарий) ----------

@app.get("/sources/{source_place}/check", response_class=HTMLResponse)
def source_check(request: Request, source_place: str):
    result = check_source_access(source_place)
    if not result.ok:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": "Площадка недоступна",
                "message": result.message,
                "version": "0.0.3",
            },
            status_code=403,
        )

    source = result.payload
    return RedirectResponse(url=f"/orders?source={source.id}", status_code=303)


# ---------- явная страница ошибки ----------

@app.get("/error", response_class=HTMLResponse)
def error_page(request: Request, reason: str = ""):
    message = reason or "Запрошенное действие не может быть выполнено."
    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "title": "Отказ системы",
            "message": message,
            "version": "0.0.3",
        },
    )


# ---------- health-check ----------

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.0.3"}
