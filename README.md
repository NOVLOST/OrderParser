```markdown
# OrderParser

**Платформа для сбора заказов на грузоперевозки с различных розничных площадок**

Версия: 0.0.2  
Статус: разработка продолжается

---

## О проекте

OrderParser — веб-приложение, которое собирает заказы на грузоперевозки с разных розничных площадок в одном окне. Цель — дать перевозчику единую платформу вместо необходимости проверять каждый сайт вручную.

Проект разрабатывается в рамках дисциплины «Методы и средства проектирования информационных систем» (4 курс).

**Текущий этап (лабораторная работа №2):** три главные функции системы и связанные с ними страницы. Реализованы создание заказа, просмотр списка и карточки, а также сценарии отказа. Данные временно хранятся в JSON-файле.

**Планируется:** постоянное хранение данных в PostgreSQL, парсинг заказов с розничных площадок (Scrapling).

---

## Технологии

| Компонент | Технология |
|---|---|
| Язык | Python 3.12 |
| Backend | FastAPI 0.115.6 |
| ASGI-сервер | Uvicorn 0.34.0 |
| Шаблоны | Jinja2 3.1.4 |
| Хранение данных | JSON-файл |
| Контейнеризация | Docker |

Планируется добавить: **Scrapling** для парсинга заказов.

---

## Структура проекта

```
project/
├── backend/
│   ├── main.py              маршруты FastAPI
│   ├── actions.py           бизнес-логика трёх функций
│   ├── storage.py           работа с JSON-файлом
│   └── requirements.txt     зависимости
├── templates/
│   ├── base.html            общий каркас
│   ├── index.html           главная
│   ├── orders.html          список заказов
│   ├── order_form.html      форма создания
│   ├── order_detail.html    карточка записи
│   └── error.html           страница отказа
├── static/
│   └── style.css            стили
├── data/
│   └── orders.json          демо-данные
├── Dockerfile
└── README.md
```

---

## Запуск

Репозиторий: https://github.com/NOVLOST/orderparser  
Ветка: lab2  
Pull Request: https://github.com/NOVLOST/orderparser/pull/2  
Образ: ixtis/orderparser:0.0.2  
Страница образа: https://hub.docker.com/r/ixtis/orderparser

```bash
docker pull ixtis/orderparser:0.0.2
docker run --rm -p 8080:8080 ixtis/orderparser:0.0.2
```

Сайт открывается по адресу http://localhost:8080

---

## Три главные функции

| Функция | Адрес |
|---|---|
| Список заказов | /orders |
| Добавить заказ | /orders/new |
| Карточка заказа | /orders/{id} |
| Отказ: заказ не найден | /orders/999 |
| Отказ: площадка не подключена | /sources/ozon/check |

---

## Сборка образа (для разработчика)

Если нужно собрать образ самостоятельно под две платформы:

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ixtis/orderparser:0.0.2 --push .
```

---

## Ссылки

- Репозиторий: https://github.com/NOVLOST/orderparser
- Pull Request лабы №2: https://github.com/NOVLOST/orderparser/pull/2
- Образ в Docker Hub: https://hub.docker.com/r/ixtis/orderparser

---

## Лицензия

Учебный проект. Свободное использование в образовательных целях.
```


