"""Бизнес-логика приложения.

Здесь лежат три главные функции OrderParser:
    1. добавить заказ (изменение данных);
    2. получить список или один заказ (просмотр);
    3. проверить доступ / корректность (ошибочный сценарий).

Маршруты в main.py вызывают эти функции и не работают с хранилищем напрямую.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from storage import (
    Order,
    Source,
    add_order as _add_order,
    get_order,
    get_source,
    load_orders,
    load_sources,
    touch_source_call,
)


# ---------- результат операции с признаком ошибки ----------

@dataclass
class ActionResult:
    """Универсальный ответ действия.

    ok=True  — всё прошло, payload содержит данные.
    ok=False — сценарий отказа, message объясняет причину для пользователя.
    """

    ok: bool
    payload: object = None
    message: str = ""

    @classmethod
    def success(cls, payload: object = None) -> "ActionResult":
        return cls(ok=True, payload=payload)

    @classmethod
    def failure(cls, message: str) -> "ActionResult":
        return cls(ok=False, message=message)


# ---------- справочник площадок ----------

def list_sources() -> list[Source]:
    """Все площадки из таблицы sources."""
    return load_sources()


# ---------- функция 1: изменение данных ----------

def create_order(
    *,
    where_from: str,
    where_to: str,
    cargo: str,
    price: str | int,
    source_place: str | int,
) -> ActionResult:
    """Создаёт заказ. Возвращает ActionResult.

    Все проверки собраны здесь, чтобы форма и API получали одинаковый ответ.
    """

    where_from = (where_from or "").strip()
    where_to = (where_to or "").strip()
    cargo = (cargo or "").strip()

    if not where_from or not where_to:
        return ActionResult.failure(
            "Не указаны пункты отправления или назначения."
        )

    if not cargo:
        return ActionResult.failure("Не указано, какой груз везём.")

    # Цена приходит из формы строкой — превращаем в число.
    try:
        price_value = int(str(price).strip())
    except (TypeError, ValueError):
        return ActionResult.failure(
            "Цена должна быть целым числом, например 45000."
        )

    if price_value <= 0:
        return ActionResult.failure("Цена должна быть больше нуля.")

    if price_value > 10_000_000:
        return ActionResult.failure("Слишком большая цена — проверьте ввод.")

    # Площадка приходит из формы строкой с id — тоже превращаем в число.
    try:
        source_id = int(str(source_place).strip())
    except (TypeError, ValueError):
        return ActionResult.failure(
            "Не выбрана площадка. Выберите одну из списка."
        )

    source = get_source(source_id)
    if source is None:
        return ActionResult.failure(
            f"Площадка с id={source_id} не найдена в справочнике."
        )

    try:
        order = _add_order(
            where_from=where_from,
            where_to=where_to,
            cargo=cargo,
            price=price_value,
            source_place=source_id,
        )
    except ValueError as exc:
        # Страховка: сюда попадём, если хранилище отклонит данные.
        return ActionResult.failure(str(exc))
    except RuntimeError as exc:
        return ActionResult.failure(f"Не удалось сохранить заказ: {exc}")

    return ActionResult.success(order)


# ---------- функция 2: просмотр данных ----------

def list_orders(source_id: Optional[int] = None) -> list[Order]:
    """Возвращает список заказов, опционально отфильтрованный по площадке."""
    return load_orders(source_id=source_id)


def get_order_card(order_id: int) -> ActionResult:
    """Возвращает карточку одного заказа или отказ, если его нет."""
    if order_id <= 0:
        return ActionResult.failure("Некорректный номер заказа.")

    order = get_order(order_id)
    if order is None:
        return ActionResult.failure(
            f"Заказ №{order_id} не найден. Возможно, он был удалён "
            f"или ещё не добавлен в систему."
        )

    return ActionResult.success(order)


# ---------- функция 3: ошибочный сценарий ----------

def check_source_access(source_place: str | int) -> ActionResult:
    """Проверяет, что площадка есть в справочнике.

    Используется, когда оператор пытается открыть заказы с площадки,
    которой нет в системе. Заодно обновляет дату последнего обращения:
    пригодится, когда появится парсинг и паузы между запросами.
    """

    try:
        source_id = int(str(source_place).strip())
    except (TypeError, ValueError):
        return ActionResult.failure(
            "Площадка не указана. Выберите одну из подключённых."
        )

    source = get_source(source_id)
    if source is None:
        available = ", ".join(s.name for s in load_sources())
        return ActionResult.failure(
            f"Площадка с id={source_id} ещё не подключена к OrderParser. "
            f"Доступные площадки: {available}."
        )

    touch_source_call(source_id)
    return ActionResult.success(source)
