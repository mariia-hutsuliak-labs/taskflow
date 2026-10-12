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

## Helm-чарт 

Чарт розгортає той самий застосунок, що й маніфести з `k8s/` (лаба №3):
backend, frontend, worker і PostgreSQL.

### version і appVersion

| Поле         | Значення | Що означає для TaskFlow                                                                 |
|--------------|----------|------------------------------------------------------------------------------------------|
| `version`    | `0.2.0`  | Версія самого чарта: шаблони, `values.yaml`, `NOTES.txt`. Змінюється, коли я правлю чарт. |
| `appVersion` | `1.0.0`  | Версія застосунку (теги образів `taskflow-backend/frontend/worker`). Змінюється з новим релізом коду. |

Приклад: якщо я додав у чарт новий прапорець, але образи ті самі, зростає тільки
`version`. Якщо вийшов застосунок `1.1.0` і чарт не змінювався, зростає тільки `appVersion`.
Реальний тег образу задається в `values.yaml` (`*.image.tag`), `appVersion` лише
інформаційний (потрапляє в мітку `app.kubernetes.io/version`).

### Namespace

Namespace у чарт не входить: Helm створює його сам прапорцем `--create-namespace`,
а `helm uninstall` не лишає в ньому об'єктів чарта. Так чарт можна встановити
в довільний namespace.

### Параметри values

| Параметр | За замовчуванням (dev) | Опис |
|----------|------------------------|------|
| `nameOverride` / `fullnameOverride` | `""` | Перевизначення імені чарта / повного імені об'єктів |
| `config.postgresDb` | `taskflow` | Назва БД |
| `config.postgresUser` | `taskflow` | Користувач БД |
| `config.pollIntervalSeconds` | `10` | Інтервал опитування БД воркером |
| `config.apiUrl` | `http://localhost:8000` | Адреса API для frontend (у браузері) |
| `secret.postgresPassword` | `taskflow-dev-password` | Пароль БД. У prod порожній, передається через `--set` |
| `backend.replicaCount` | `1` | Кількість реплік backend |
| `backend.image.repository` / `.tag` / `.pullPolicy` | `ghcr.io/mariia-hutsuliak-labs/taskflow-backend` / `1.0.0` / `IfNotPresent` | Образ backend |
| `backend.service.port` | `8000` | Порт Service і контейнера backend |
| `backend.resources` | requests 100m/128Mi, limits 500m/256Mi | Ресурси backend |
| `frontend.replicaCount` | `1` | Кількість реплік frontend |
| `frontend.image.repository` / `.tag` / `.pullPolicy` | `ghcr.io/mariia-hutsuliak-labs/taskflow-frontend` / `1.0.0` / `IfNotPresent` | Образ frontend |
| `frontend.containerPort` | `80` | Порт контейнера frontend |
| `frontend.service.type` | `NodePort` | Тип Service frontend |
| `frontend.service.port` | `80` | Порт Service frontend |
| `frontend.service.nodePort` | `null` | Фіксований nodePort (лише для `NodePort`); порожній, щоб можна було встановити чарт двічі |
| `frontend.resources` | requests 50m/32Mi, limits 200m/128Mi | Ресурси frontend |
| `worker.replicaCount` | `1` | Кількість реплік worker |
| `worker.image.repository` / `.tag` / `.pullPolicy` | `ghcr.io/mariia-hutsuliak-labs/taskflow-worker` / `1.0.0` / `IfNotPresent` | Образ worker |
| `worker.resources` | requests 50m/64Mi, limits 200m/128Mi | Ресурси worker |
| `db.replicaCount` | `1` | Кількість реплік БД |
| `db.image.repository` / `.tag` | `postgres` / `16-alpine` | Образ PostgreSQL (також для initContainer `wait-for-db`) |
| `db.service.port` | `5432` | Порт PostgreSQL |
| `db.persistence.enabled` | `true` | Створювати PersistentVolumeClaim (інакше `emptyDir`) |
| `db.persistence.size` / `.storageClass` / `.accessMode` | `1Gi` / `standard` / `ReadWriteOnce` | Параметри PVC |
| `db.resources` | requests 100m/128Mi, limits 500m/512Mi | Ресурси БД |
| `ingress.enabled` | `false` | Створювати Ingress |
| `ingress.className` | `nginx` | Клас Ingress |
| `ingress.host` | `taskflow.local` | Хост Ingress |
| `ingress.apiPaths` | `/tasks`, `/health`, `/docs`, `/openapi.json` | Шляхи, що ведуть на backend (решта `/` на frontend) |
| `hooks.preUpgrade.enabled` | `true` | Job-хук `pre-upgrade`: перевіряє доступність БД перед оновленням |
| `tests.enabled` | `true` | Под для `helm test` (перевірка backend `/health` і frontend `/`) |
| `tests.image.repository` / `.tag` | `busybox` / `1.36` | Образ тестового пода |

Dev і prod відрізняються файлами `values-dev.yaml` і `values-prod.yaml`:

| | dev | prod |
|---|-----|------|
| Репліки backend / frontend | 1 / 1 | 3 / 3 |
| Теги образів | `1.0.0` | `1.1.0` |
| Ресурси | малі | збільшені |
| Ingress | вимкнений | увімкнений (`taskflow.local`) |
| Service frontend | `NodePort` | `ClusterIP` |
| PVC | `1Gi` | `5Gi` |

### Перевірка чарта

```bash
helm lint helm/taskflow
helm lint helm/taskflow -f helm/taskflow/values-prod.yaml --set secret.postgresPassword=test
helm template taskflow helm/taskflow -n taskflow
```

### Різниця між середовищами (без встановлення в кластер)

```bash
diff \
  <(helm template taskflow helm/taskflow -n taskflow -f helm/taskflow/values-dev.yaml) \
  <(helm template taskflow helm/taskflow -n taskflow -f helm/taskflow/values-prod.yaml --set secret.postgresPassword=test)
```

### Встановлення

Dev:

```bash
helm install taskflow helm/taskflow -n taskflow --create-namespace \
  -f helm/taskflow/values-dev.yaml
```

Prod (пароль не зберігається у файлах):

```bash
export TASKFLOW_DB_PASSWORD='<пароль>'
helm install taskflow helm/taskflow -n taskflow --create-namespace \
  -f helm/taskflow/values-prod.yaml \
  --set secret.postgresPassword="$TASKFLOW_DB_PASSWORD"
```

Другий екземпляр в той самий кластер (інше ім'я релізу, namespace і хост Ingress):

```bash
helm install taskflow-2 helm/taskflow -n taskflow-2 --create-namespace \
  -f helm/taskflow/values-dev.yaml
```

### Пріоритет значень

Від найнижчого до найвищого:

1. `values.yaml` у чарті (значення за замовчуванням);
2. файли `-f` / `--values`; якщо їх кілька, пізніший перекриває попередній;
3. прапорці `--set` (і `--set-string`, `--set-file`), найвищий пріоритет.

Приклад: `-f values-prod.yaml --set backend.replicaCount=5` дасть 5 реплік, хоча
у файлі `3`; а `frontend.image.tag`, якого немає ні у файлі, ні в `--set`,
візьметься з `values.yaml`.

### Хук і тест релізу

- `templates/pre-upgrade-job.yaml` - Job з анотацією `helm.sh/hook: pre-upgrade`.
  Запускається перед кожним `helm upgrade` і перевіряє, що PostgreSQL доступний.
  Якщо база недоступна, оновлення не відбувається.
- `templates/tests/test-connection.yaml` - под з анотацією `helm.sh/hook: test`.
  Запускається командою `helm test` і перевіряє `/health` backend та `/` frontend.

```bash
helm test taskflow -n taskflow --logs
helm upgrade taskflow helm/taskflow -n taskflow -f helm/taskflow/values-dev.yaml --set backend.image.tag=1.1.0
kubectl get jobs -n taskflow
kubectl logs job/taskflow-pre-upgrade-check -n taskflow
```

Об'єкти-хуки не входять до релізу, тому `helm uninstall` їх не видаляє:

```bash
kubectl delete job,pod -n taskflow -l app.kubernetes.io/instance=taskflow
```
