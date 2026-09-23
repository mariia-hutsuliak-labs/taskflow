# TaskFlow

Невеликий сервіс керування задачами (todo-менеджер), зроблений як навчальний
проєкт для лабораторних робіт з DevOps.

## Архітектура

Проєкт складається з трьох незалежних частин (мікросервісів) і бази даних:

- **backend** — FastAPI веб-застосунок, REST API для задач (CRUD), працює з PostgreSQL.
- **frontend** — статична веб-сторінка (HTML/CSS/JS), яка звертається до backend API: список задач, форма додавання, позначення виконаною, видалення. Роздається через nginx.
- **worker** — окремий фоновий процес, який раз на N секунд опитує ту саму БД
  і виводить у лог задачі, що прострочені.
- **db** — PostgreSQL 16.

```
taskflow/
├── .github/workflows/
│   └── ci.yml          # CI-пайплайн
├── backend/
│   ├── app/            # код FastAPI застосунку
│   ├── tests/          # юніт + інтеграційні тести (pytest)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── utils.js
│   ├── tests/          # тести (node --test)
│   ├── build.js
│   ├── package.json
│   └── Dockerfile
├── worker/
│   ├── worker.py
│   ├── test_worker.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── ruff.toml
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

```bash
cd frontend
npm ci
npm run lint
npm test
```

## CI/CD

Пайплайн на GitHub Actions: `.github/workflows/ci.yml`.
Запускається на Pull Request у `main` і на push у `main`.

- **backend, worker** — Ruff, збірка, pytest (кеш pip)
- **frontend** — ESLint, `npm run build`, `node --test` (кеш npm)
- **Docker image** — запускається після успіху всіх попередніх: збірка образу,
  сканування Trivy, публікація в ghcr.io (тільки для push)

Теги образів: `sha-<коміт>` і `latest` (тільки `main`).

```bash
docker pull ghcr.io/mariiahutsuliak/taskflow-backend:latest
docker run --rm -p 8000:8000 -e DATABASE_URL=sqlite:////tmp/taskflow.db \
  ghcr.io/mariiahutsuliak/taskflow-backend:latest
```