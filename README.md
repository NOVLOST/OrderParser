```markdown
# OrderParser

**Платформа для сбора заказов на грузоперевозки с различных розничных площадок**

Версия: 0.0.3  
Статус: разработка продолжается

---

## О проекте

OrderParser — веб-приложение, которое собирает заказы на грузоперевозки с разных розничных площадок в одном окне. Цель — дать перевозчику единую платформу вместо необходимости проверять каждый сайт вручную.

Проект разрабатывается в рамках дисциплины «Методы и средства проектирования информационных систем» (4 курс).

**Текущий этап (лабораторная работа №3):** постоянное хранение данных. Данные трёх функций перенесены из JSON-файла в PostgreSQL, который поднимается отдельным сервисом вместе с приложением через `docker compose`.

**Планируется:** парсинг заказов с розничных площадок (Scrapling), фильтрация и поиск.

---

## Технологии

| Компонент | Технология |
|---|---|
| Язык | Python 3.12 |
| Backend | FastAPI 0.115.6 |
| ASGI-сервер | Uvicorn 0.34.0 |
| Шаблоны | Jinja2 3.1.4 |
| База данных | PostgreSQL 16 |
| Драйвер БД | psycopg 3.2.3 |
| Контейнеризация | Docker, Docker Compose |

Планируется добавить: **Scrapling** для парсинга заказов.

---

## Структура проекта

```
```
project/
├── backend/
│   ├── main.py              маршруты FastAPI
│   ├── actions.py           бизнес-логика трёх функций
│   ├── storage.py           работа с PostgreSQL
│   └── requirements.txt     зависимости
├── templates/               шаблоны Jinja2
├── static/                  стили
├── Dockerfile
├── docker-compose.yml
└── README.md
```
```
---

## Запуск

Репозиторий: https://github.com/NOVLOST/OrderParser/
Ветка: lab3  
Pull Request: https://github.com/NOVLOST/orderparser/pull/3  
Образ: ixtis/orderparser:0.0.3  
Страница образа: https://hub.docker.com/r/NOVLOST/orderparser

```bash
git clone -b lab3 https://github.com/NOVLOST/orderparser
cd orderparser
docker compose up -d
```

Сайт открывается по адресу http://localhost:8080

---

## Проверка работы

1. Открыть http://localhost:8080 — на главной версия 0.0.3.
2. Перейти в «Список заказов» — после первого запуска список пустой.
3. Добавить заказ через форму «Добавить заказ».
4. Убедиться, что запись появилась в списке.
5. Выполнить:

```bash
docker compose down
docker compose up -d
```

6. Открыть список снова — запись на месте.

Флага `-v` в командах нет: том `dbdata` с данными сохраняется между перезапусками.

---

## Сборка образа (для разработчика)

Если нужно собрать образ самостоятельно под две платформы:

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ixtis/orderparser:0.0.3 --push .
```

---

## Ссылки

- Репозиторий: https://github.com/NOVLOST/orderparser
- Pull Request лабы №3: https://github.com/NOVLOST/orderparser/pull/3
- Образ в Docker Hub: https://hub.docker.com/r/NOVLOST/orderparser

---

## Лицензия

Учебный проект. Свободное использование в образовательных целях.
```
