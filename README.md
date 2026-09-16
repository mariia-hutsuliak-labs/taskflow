# TaskFlow

Невеликий сервіс керування задачами (todo-менеджер), зроблений як навчальний
проєкт для лабораторної роботи з DevOps: "Віртуалізація та контейнеризація".

## Архітектура

Проєкт складається з трьох незалежних частин (мікросервісів) і бази даних:

- **backend** — FastAPI веб-застосунок, REST API для задач (CRUD), працює з PostgreSQL.
- **frontend** — статична веб-сторінка (HTML/CSS/JS), яка звертається до backend API: список задач, форма додавання, позначення виконаною, видалення. Роздається через nginx.
- **worker** — окремий фоновий процес, який раз на N секунд опитує ту саму БД
  і виводить у лог задачі, що прострочені.
- **db** — PostgreSQL 16.

```
taskflow/
├── backend/
│   ├── app/            # код FastAPI застосунку
│   ├── tests/          # юніт + інтеграційні тести (pytest)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── Dockerfile
├── worker/
│   ├── worker.py
│   ├── test_worker.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
└── README.md
```

## Як запустити

```bash
docker compose up --build
```

Після старту:
- Веб-інтерфейс — http://localhost:3000
- API доступне на http://localhost:8000
- Документація Swagger — http://localhost:8000/docs
- Health check: `GET /health`

### Основні ендпоінти

| Метод | Шлях                      | Опис                          |
|-------|---------------------------|--------------------------------|
| POST  | /tasks                    | Створити задачу                |
| GET   | /tasks                    | Список задач                   |
| GET   | /tasks/{id}                | Отримати одну задачу           |
| PATCH | /tasks/{id}/complete        | Позначити задачу виконаною     |
| DELETE| /tasks/{id}                | Видалити задачу                |

Приклад створення задачі:

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Здати лабу", "due_date": "2026-09-20T12:00:00"}'
```

## Тести

Тести використовують SQLite in-memory замість реальної Postgres, тому
запускаються без піднятих контейнерів:

```bash
cd backend
pip install -r requirements.txt
pytest
```

```bash
cd worker
pip install -r requirements.txt
pytest
```

## Відповідність вимогам лабораторної

1. Проєкт — веб-застосунок (FastAPI) + PostgreSQL БД. ✅
2. Юніт та інтеграційні тести (pytest). ✅
3. Складається з декількох частин: `backend` + `worker` (знадобиться для
   лабораторної з мікросервісами). ✅
4. Dockerfile для кожної частини (`backend/Dockerfile`, `worker/Dockerfile`). ✅
5. `docker-compose.yml`, що піднімає весь проєкт разом з БД. ✅
