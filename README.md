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
├── k8s/                # маніфести Kubernetes (лаба 3)
├── docker-compose.yml
├── ruff.toml
└── README.md
```

## Як запустити (Docker Compose)

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
Запускається на Pull Request у `main`, на push у `main` і на push тегів `v*.*.*`.

- **backend, worker** — Ruff, збірка, pytest (кеш pip)
- **frontend** — ESLint, `npm run build`, `node --test` (кеш npm)
- **Docker image** — запускається після успіху всіх попередніх: збірка образу
  (`linux/amd64` і `linux/arm64`), сканування Trivy, публікація в ghcr.io
  (тільки для push)

Теги образів: `sha-<коміт>`, `latest` (тільки `main`) і версія `X.Y.Z`
(для git-тегу `vX.Y.Z`). Для Kubernetes використовуються лише версійні теги.

```bash
docker pull ghcr.io/mariia-hutsuliak-labs/taskflow-backend:1.1.0
docker run --rm -p 8000:8000 -e DATABASE_URL=sqlite:////tmp/taskflow.db \
  ghcr.io/mariia-hutsuliak-labs/taskflow-backend:1.1.0
```

## Розгортання в Kubernetes (minikube)

Маніфести лежать у каталозі `k8s/`, по одному об'єкту на файл. Номери
у назвах задають порядок застосування.

| Файл                          | Об'єкт                                    |
|-------------------------------|-------------------------------------------|
| `00-namespace.yaml`           | Namespace `taskflow`                      |
| `01-configmap.yaml`           | ConfigMap `taskflow-config`               |
| `02-secret.yaml`              | Secret `taskflow-secret`                  |
| `10-db-pvc.yaml`              | PersistentVolumeClaim `db-data`           |
| `11-db-deployment.yaml`       | Deployment `db` (PostgreSQL)              |
| `12-db-service.yaml`          | Service `db` (ClusterIP)                  |
| `20-backend-deployment.yaml`  | Deployment `backend` (2 репліки)          |
| `21-backend-service.yaml`     | Service `backend` (ClusterIP)             |
| `30-frontend-deployment.yaml` | Deployment `frontend` (2 репліки)         |
| `31-frontend-service.yaml`    | Service `frontend` (NodePort 30080)       |
| `40-worker-deployment.yaml`   | Deployment `worker`                       |
| `50-ingress.yaml`             | Ingress `taskflow` (хост `taskflow.local`)|

### Вимоги

- Docker, minikube, kubectl
- Образи `taskflow-backend`, `taskflow-frontend`, `taskflow-worker` версії
  `1.0.0` та `1.1.0` у `ghcr.io/mariia-hutsuliak-labs/`

### Порядок розгортання

1. Запустити кластер і додатки:

```bash
   minikube start --driver=docker
   minikube addons enable ingress
   minikube addons enable metrics-server
```

2. Розгорнути все однією командою з кореня репозиторію:

```bash
   kubectl apply -f k8s/
```

   `kubectl` застосовує файли за алфавітом, тому Namespace, ConfigMap і
   Secret створюються раніше за Deployment, які їх використовують.

3. Дочекатися готовності й переглянути об'єкти:

```bash
   kubectl get pods -n taskflow -w
   kubectl get all,ingress,pvc,configmap,secret -n taskflow
```

   Backend чекає на базу через initContainer `wait-for-db`, тому на початку
   його поди кілька секунд мають статус `Init`.

4. Відкрити застосунок. Додати у `/etc/hosts` рядок:

```
   127.0.0.1 taskflow.local
```

   і залишити в окремому терміналі запущену команду (потрібен пароль):

```bash
   minikube tunnel
```

   Застосунок: http://taskflow.local, API: http://taskflow.local/docs.

   Альтернатива через NodePort: `minikube service frontend -n taskflow --url`.

### Параметри ConfigMap `taskflow-config`

| Ключ                    | Значення              | Призначення                                      |
|-------------------------|-----------------------|--------------------------------------------------|
| `POSTGRES_DB`           | `taskflow`            | Назва бази даних PostgreSQL                      |
| `POSTGRES_USER`         | `taskflow`            | Користувач бази даних                            |
| `POLL_INTERVAL_SECONDS` | `10`                  | Інтервал опитування БД воркером                  |
| `API_URL`               | `http://taskflow.local` | Адреса API, яку frontend бере у `config.js`    |

### Параметри Secret `taskflow-secret`

Значення в репозиторії навчальні, не реальні паролі.

| Ключ                | Призначення                                                    |
|---------------------|----------------------------------------------------------------|
| `POSTGRES_PASSWORD` | Пароль користувача PostgreSQL                                  |
| `DATABASE_URL`      | Рядок підключення до БД для backend і worker (містить пароль)  |

### Оновлення та відкат

```bash
kubectl set image deployment/frontend \
  frontend=ghcr.io/mariia-hutsuliak-labs/taskflow-frontend:1.1.0 -n taskflow
kubectl rollout status deployment/frontend -n taskflow
kubectl rollout history deployment/frontend -n taskflow
kubectl rollout undo deployment/frontend -n taskflow
```

Стратегія оновлення — `RollingUpdate` з `maxUnavailable: 0`, тому під час
оновлення застосунок лишається доступним.

### Видалення

```bash
kubectl delete -f k8s/
```