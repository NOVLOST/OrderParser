"""Точка входа приложения OrderParser.

Здесь только маршруты и рендеринг шаблонов.
Бизнес-логика — в actions.py, работа с файлом — в storage.py.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from actions import (
    ALLOWED_SOURCES,
    check_source_access,
    create_order,
    get_order_card,
    list_orders,
)


# ---------- приложение и шаблоны ----------

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="OrderParser", version="0.0.2")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# ---------- главная ----------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "version": "0.0.2",
        },
    )


# ---------- просмотр списка ----------

@app.get("/orders", response_class=HTMLResponse)
def orders_list(request: Request, source: str | None = None):
    orders = list_orders(source=source)
    return templates.TemplateResponse(
        "orders.html",
        {
            "request": request,
            "orders": orders,
            "source": source or "",
            "allowed_sources": sorted(ALLOWED_SOURCES),
            "version": "0.0.2",
        },
    )


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
                "version": "0.0.2",
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        "order_detail.html",
        {
            "request": request,
            "order": result.payload,
            "version": "0.0.2",
        },
    )


# ---------- форма создания (GET) ----------

@app.get("/orders/new", response_class=HTMLResponse)
def order_new_form(request: Request):
    return templates.TemplateResponse(
        "order_form.html",
        {
            "request": request,
            "allowed_sources": sorted(ALLOWED_SOURCES),
            "form": {},
            "error": "",
            "version": "0.0.2",
        },
    )


# ---------- форма создания (POST) ----------

@app.post("/orders/new", response_class=HTMLResponse)
def order_new_submit(
    request: Request,
    origin: str = Form(""),
    destination: str = Form(""),
    cargo: str = Form(""),
    price: str = Form(""),
    source: str = Form("manual"),
):
    result = create_order(
        origin=origin,
        destination=destination,
        cargo=cargo,
        price=price,
        source=source,
    )

    if not result.ok:
        # Возвращаем форму с тем же вводом и текстом ошибки.
        return templates.TemplateResponse(
            "order_form.html",
            {
                "request": request,
                "allowed_sources": sorted(ALLOWED_SOURCES),
                "form": {
                    "origin": origin,
                    "destination": destination,
                    "cargo": cargo,
                    "price": price,
                    "source": source,
                },
                "error": result.message,
                "version": "0.0.2",
            },
            status_code=400,
        )

    # После успеха — на список, чтобы новая запись была видна.
    return RedirectResponse(url="/orders", status_code=303)


# ---------- проверка доступа к площадке (ошибочный сценарий) ----------

@app.get("/sources/{source}/check", response_class=HTMLResponse)
def source_check(request: Request, source: str):
    result = check_source_access(source)
    if not result.ok:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "title": "Площадка недоступна",
                "message": result.message,
                "version": "0.0.2",
            },
            status_code=403,
        )

    return RedirectResponse(url=f"/orders?source={result.payload}", status_code=303)


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
            "version": "0.0.2",
        },
    )


# ---------- health-check (на будущее) ----------

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.0.2"}
