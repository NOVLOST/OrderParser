
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

from storage import Order, add_order as _add_order, get_order, load_orders


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


# ---------- допустимые площадки ----------

ALLOWED_SOURCES = {"manual", "avito", "ati", "della"}


# ---------- функция 1: изменение данных ----------

def create_order(
    *,
    origin: str,
    destination: str,
    cargo: str,
    price: str | int,
    source: str = "manual",
) -> ActionResult:
    """Создаёт заказ. Возвращает ActionResult.

    Все проверки собраны здесь, чтобы форма и API получали одинаковый ответ.
    """

    origin = (origin or "").strip()
    destination = (destination or "").strip()
    cargo = (cargo or "").strip()

    if not origin or not destination:
        return ActionResult.failure(
            "Не указаны пункты отправления или назначения."
        )

    if not cargo:
        return ActionResult.failure("Не указано, какой груз везём.")

    # Цена приходит из формы строкой — пробуем превратить в число.
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

    if source not in ALLOWED_SOURCES:
        return ActionResult.failure(
            f"Площадка «{source}» не поддерживается. "
            f"Допустимые: {', '.join(sorted(ALLOWED_SOURCES))}."
        )

    try:
        order = _add_order(
            origin=origin,
            destination=destination,
            cargo=cargo,
            price=price_value,
            source=source,
        )
    except ValueError as exc:
        # Страховка: сюда попадём, если хранилище отклонит данные.
        return ActionResult.failure(str(exc))
    except RuntimeError as exc:
        return ActionResult.failure(
            f"Не удалось сохранить заказ: {exc}"
        )

    return ActionResult.success(order)


# ---------- функция 2: просмотр данных ----------

def list_orders(source: Optional[str] = None) -> list[Order]:
    """Возвращает список заказов, опционально отфильтрованный по площадке."""
    orders = load_orders()
    if source:
        orders = [o for o in orders if o.source == source]
    return orders


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

def check_source_access(source: str) -> ActionResult:
    """Проверяет, разрешён ли доступ к площадке.

    Используется, когда оператор пытается открыть заказы с площадки,
    которая не подключена к системе.
    """

    source = (source or "").strip().lower()

    if not source:
        return ActionResult.failure(
            "Площадка не указана. Выберите одну из подключённых."
        )

    if source not in ALLOWED_SOURCES:
        return ActionResult.failure(
            f"Площадка «{source}» ещё не подключена к OrderParser. "
            f"Доступные площадки: {', '.join(sorted(ALLOWED_SOURCES))}."
        )

    return ActionResult.success(source)
