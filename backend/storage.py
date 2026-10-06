
"""Слой работы с данными.

Заказы хранятся в JSON-файле. Файл читается при каждом обращении,
запись выполняется атомарно: сначала во временный файл, потом замена
исходного. Это защищает данные от повреждения при падении процесса.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Iterable, Optional


# Путь к файлу данных. Можно переопределить переменной окружения,
# чтобы удобно подменять его в тестах или в контейнере.
DATA_FILE = Path(os.getenv("ORDERS_DATA_FILE", "data/orders.json"))

# Блокировка на время записи. FastAPI может обрабатывать запросы
# в нескольких потоках — так мы не допустим одновременной записи.
_write_lock = Lock()


@dataclass
class Order:
    """Один заказ на грузоперевозку."""

    id: int
    origin: str            # откуда
    destination: str       # куда
    cargo: str             # что везём
    price: int             # цена, рубли
    source: str = "manual" # откуда пришёл заказ: manual, avito, ati, ...
    status: str = "new"    # new, in_progress, done, cancelled

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "Order":
        """Создаёт Order из словаря, отбрасывая лишние поля."""
        allowed = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in allowed})


# ---------- низкоуровневые операции с файлом ----------

def _ensure_file() -> None:
    """Создаёт файл и родительскую папку, если их ещё нет."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def _read_raw() -> list[dict]:
    """Читает JSON и возвращает список словарей."""
    _ensure_file()
    try:
        content = DATA_FILE.read_text(encoding="utf-8").strip() or "[]"
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Файл данных повреждён: {DATA_FILE}") from exc

    if not isinstance(data, list):
        raise RuntimeError(f"Ожидался список заказов в {DATA_FILE}")
    return data


def _write_raw(items: list[dict]) -> None:
    """Атомарно записывает список словарей в JSON-файл."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Пишем во временный файл рядом с целевым, чтобы os.replace
    # работал в пределах одной файловой системы.
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=DATA_FILE.parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        json.dump(items, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)

    os.replace(tmp_path, DATA_FILE)


# ---------- публичный API ----------

def load_orders() -> list[Order]:
    """Возвращает все заказы."""
    return [Order.from_dict(row) for row in _read_raw()]


def get_order(order_id: int) -> Optional[Order]:
    """Возвращает заказ по id или None, если такого нет."""
    for order in load_orders():
        if order.id == order_id:
            return order
    return None


def save_orders(orders: Iterable[Order]) -> None:
    """Полностью перезаписывает файл переданным списком заказов."""
    payload = [order.to_dict() for order in orders]
    with _write_lock:
        _write_raw(payload)


def add_order(
    *,
    origin: str,
    destination: str,
    cargo: str,
    price: int,
    source: str = "manual",
    status: str = "new",
) -> Order:
    """Добавляет новый заказ и возвращает его с присвоенным id."""
    if not origin or not destination:
        raise ValueError("Пункты отправления и назначения обязательны")
    if price < 0:
        raise ValueError("Цена не может быть отрицательной")

    with _write_lock:
        orders = [Order.from_dict(row) for row in _read_raw()]
        next_id = max((o.id for o in orders), default=0) + 1

        order = Order(
            id=next_id,
            origin=origin.strip(),
            destination=destination.strip(),
            cargo=cargo.strip(),
            price=int(price),
            source=source,
            status=status,
        )
        orders.append(order)
        _write_raw([o.to_dict() for o in orders])

    return order
