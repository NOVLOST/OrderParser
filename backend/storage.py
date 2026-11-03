"""Слой работы с данными — PostgreSQL.

Заказы и площадки хранятся в PostgreSQL. Подключение берётся из переменной
DATABASE_URL, которую задаёт docker-compose.yml. Схема создаётся при старте
приложения: init_schema().
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional

import psycopg
from psycopg.rows import dict_row


# Адрес БД. Значение по умолчанию совпадает с docker-compose.yml,
# но в контейнере всегда подставляется переменной окружения.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://app:app@db:5432/app",
)

# Справочник площадок. Создаётся один раз при первом запуске.
DEFAULT_SOURCES = [
    "Ручной ввод",
    "Avito",
    "ATI.SU",
    "Della",
]


# ---------- модели ----------

@dataclass
class Source:
    id: int
    name: str
    date_last_call: Optional[datetime] = None


@dataclass
class Order:
    id: int
    where_from: str
    where_to: str
    cargo: str
    price: int
    date: datetime
    source_place: int
    source_name: Optional[str] = None  # заполняется при JOIN


# ---------- подключение ----------

@contextmanager
def _connect() -> Iterator[psycopg.Connection]:
    """Открывает соединение и закрывает после блока with."""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def _connect_with_retry(
    max_attempts: int = 15,
    delay: float = 2.0,
) -> psycopg.Connection:
    """Подключается, повторяя попытки, пока PostgreSQL не будет готов.

    depends_on в docker-compose ждёт только старта контейнера, а не
    готовности СУБД принимать подключения. Поэтому стучимся несколько раз.
    """
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return psycopg.connect(DATABASE_URL, row_factory=dict_row)
        except psycopg.OperationalError as exc:
            last_error = exc
            print(f"[storage] БД не готова ({attempt}/{max_attempts}): {exc}")
            time.sleep(delay)

    raise RuntimeError(
        f"Не удалось подключиться к БД за {max_attempts} попыток"
    ) from last_error


# ---------- создание схемы ----------

def init_schema() -> None:
    """Создаёт таблицы и заполняет справочник площадок.

    Вызывается один раз при старте приложения. Повторные вызовы безопасны:
    CREATE TABLE IF NOT EXISTS и ON CONFLICT DO NOTHING ничего не ломают.
    """
    conn = _connect_with_retry()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sources (
                    id              SERIAL PRIMARY KEY,
                    name            VARCHAR(200) NOT NULL UNIQUE,
                    date_last_call  TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id              SERIAL PRIMARY KEY,
                    where_from      VARCHAR(200) NOT NULL,
                    where_to        VARCHAR(200) NOT NULL,
                    cargo           VARCHAR(500) NOT NULL,
                    price           INTEGER NOT NULL CHECK (price > 0),
                    date            TIMESTAMP NOT NULL DEFAULT NOW(),
                    source_place    INTEGER NOT NULL
                                    REFERENCES sources(id) ON DELETE RESTRICT
                );
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_orders_source_place
                ON orders(source_place);
            """)

            for name in DEFAULT_SOURCES:
                cur.execute(
                    "INSERT INTO sources (name) VALUES (%s) "
                    "ON CONFLICT (name) DO NOTHING;",
                    (name,),
                )

        conn.commit()
        print("[storage] Схема готова, справочник площадок заполнен")
    finally:
        conn.close()


# ---------- площадки ----------

def load_sources() -> list[Source]:
    """Возвращает все площадки."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, date_last_call FROM sources ORDER BY id;"
        )
        rows = cur.fetchall()
    return [Source(**row) for row in rows]


def get_source(source_id: int) -> Optional[Source]:
    """Возвращает площадку по id или None."""
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, date_last_call FROM sources WHERE id = %s;",
            (source_id,),
        )
        row = cur.fetchone()
    return Source(**row) if row else None


def touch_source_call(source_id: int) -> None:
    """Обновляет дату последнего обращения к площадке.

    Пригодится, когда появится парсинг: перед новым запросом проверяем,
    сколько прошло с прошлого, чтобы не перегружать сервер площадки.
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE sources SET date_last_call = NOW() WHERE id = %s;",
            (source_id,),
        )
        conn.commit()


# ---------- заказы ----------

def load_orders(source_id: Optional[int] = None) -> list[Order]:
    """Возвращает заказы. Если передан source_id — только этого источника."""
    sql = """
        SELECT
            o.id,
            o.where_from,
            o.where_to,
            o.cargo,
            o.price,
            o.date,
            o.source_place,
            s.name AS source_name
        FROM orders o
        JOIN sources s ON s.id = o.source_place
    """
    params: tuple = ()

    if source_id is not None:
        sql += " WHERE o.source_place = %s"
        params = (source_id,)

    sql += " ORDER BY o.id;"

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    return [Order(**row) for row in rows]


def get_order(order_id: int) -> Optional[Order]:
    """Возвращает заказ по id или None."""
    sql = """
        SELECT
            o.id,
            o.where_from,
            o.where_to,
            o.cargo,
            o.price,
            o.date,
            o.source_place,
            s.name AS source_name
        FROM orders o
        JOIN sources s ON s.id = o.source_place
        WHERE o.id = %s;
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (order_id,))
        row = cur.fetchone()

    return Order(**row) if row else None


def add_order(
    *,
    where_from: str,
    where_to: str,
    cargo: str,
    price: int,
    source_place: int,
) -> Order:
    """Добавляет заказ и возвращает его с присвоенным id."""
    if not where_from or not where_to:
        raise ValueError("Пункты отправления и назначения обязательны")
    if price <= 0:
        raise ValueError("Цена должна быть больше нуля")

    sql = """
        INSERT INTO orders (where_from, where_to, cargo, price, source_place)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, where_from, where_to, cargo, price, date, source_place;
    """

    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            sql,
            (
                where_from.strip(),
                where_to.strip(),
                cargo.strip(),
                int(price),
                source_place,
            ),
        )
        row = cur.fetchone()
        conn.commit()

    # Подтягиваем имя площадки, чтобы шаблоны могли показать его сразу.
    order = Order(**row)
    source = get_source(order.source_place)
    if source:
        order.source_name = source.name
    return order
