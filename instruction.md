# ATLAS — Інструкція реалізації (зведена & операційна)

Коротко: цей файл — поетапна, технічно-орієнтована інструкція для реалізації ATLAS (Kubernetes, RAG, MCP Hub, LLM1/2/3). Мета — дати репозиторію одну однозначну, тестовану та операційно-придатну версію плану.

Зміни в цьому файлі повинні бути лаконічними: архітектурні рішення — в `docs/adr/`, маніфести — в `infra/k8s/`, дашборди — в `infra/monitoring/grafana/`.

## Швидкий чеклист (що має бути реалізовано)

- Підготувати `k8s/` маніфести для всіх сервісів (композиція → k8s, ручні правки для stateful сервісів).
- Налаштувати StorageClass та PVC для Qdrant/Milvus і Redis, додати бекап-процедури.
- Розгорнути Prometheus + Grafana; експортувати початкові dashboards у JSON у `infra/monitoring/grafana/`.
- Впровадити Secrets, RBAC, NetworkPolicy для захисту.
- Реалізувати RAG (chunking, embedding, індексація, retrieval) з Redis як семантичним кешем.
- Створити абстракцію LLM-провайдерів; LLM2 — локальна Ollama (`gpt-oss:latest`) за замовчуванням.
- Розгорнути MCP Hub з Playwright, Automation, TTS, macOS MCP і telemetry → Prometheus.
- Розгорнути Falco → потік подій → LLM3 із політиками автоматизації + audit trail.
- Реалізувати Agent Registry, Team Constructor з human-in-the-loop.
- Створити CI: lint(k8s, code) → unit → integration → optional staging deploy → E2E.

> Нові доповнення цієї версії: деталізовано MCP Hub (архітектура, контракти, метрики й авто-вибір), Live Debate Mode, Реєстр агентів і Конструктор команд (схеми/CRUD/API), розширено політики безпеки (таблиця Falco→дії LLM3), ізоляцію Playwright/Kasm/Apple container, приклади K8s маніфестів, більш повний `.env.example`, детальні сценарії тестування, ASCII-діаграми, глосарій, FAQ, PromQL і DR/Backup план.

## Структура репозиторію (рекомендована)

```text
atlas/
├── agents/
│   ├── llm1/
│   ├── llm2/
│   └── llm3/
├── mcp/
│   ├── servers/
│   └── client/
├── infra/
│   ├── k8s/
│   └── monitoring/
├── docs/
│   └── adr/
├── web/
│   └── ui/
├── scripts/
└── tests/
```

## Фази реалізації (коротко)

Кожна фаза має контрольну точку з тестами та критеріями прийняття.

### Фаза 1 — Інфраструктура (INF-01, INF-02, OBS-01, OPS-01)

Ціль: конвертувати `compose.yaml` в якісні K8s маніфести, забезпечити персистентність та базовий моніторинг.

Ключові кроки:

- Створити `infra/k8s/` та запустити:

```bash
# з корню репо
kompose convert -f compose.yaml -o infra/k8s/kompose-generated/
```

- Ручні доопрацювання:

  - замінити базу даних Deployments → StatefulSet з `volumeClaimTemplates`;
  - додати readiness/liveness probes;
  - прописати resources.requests/limits;
  - додати podAntiAffinity для критичних сервісів;
  - протестувати manifests через `kubeval`/`kubeconform`.

- Розгорнути Prometheus & Grafana у `observability` namespace та зберегти початкові JSON дашборди у `infra/monitoring/grafana/initial-dashboard.json`.

Критерії приймання:

- PVC зберігають дані після рестарту pod;
- Prometheus збирає базові метрики; Grafana показує початкову панель;
- manifests проходять валідацію лінтером.

### Фаза 2 — Core agents і RAG (MEM-01, CFG-01, CFG-02, ORC-01)

Ціль: реалізувати RAG для LLM1 та LLM2 як локальний оркестратор з Ollama.

Ключові кроки:

- RAG: chunking → embedding → store в Qdrant/Milvus; semantic cache в Redis (TTL + similarity threshold).
- Абстракція LLM provider: інтерфейс для OpenAI/Mistral/Gemini/Ollama; конфігурований fallback chain.
- LLM2: забезпечити запуск локальної Ollama (`gpt-oss:latest`), healthcheck endpoint і audit-логування фолбеків.
- Linear tool: GraphQL client з retry/circuit-breaker.

Тести:

- unit для chunking, embeddings, provider abstraction;
- integration: LLM1↔RAG, LLM2↔Ollama, Linear tool in test project;
- E2E: full user → LLM1 (RAG) → LLM2 (plan + create issue).

### Фаза 3 — MCP Hub, Automation, Security (MCP-01..MCP-06, SEC-01, GUI-01)

Ціль: побудувати MCP Hub, забезпечити ізольоване виконання Playwright і інтегрувати Falco → LLM3.

Ключові кроки:

- Реєстр MCP: `ATLAS_MCP_SERVERS` або Service Discovery; контракти HTTP/gRPC та auth tokens.
- Playwright MCP: запуск в ізольованому контейнері, обмежений NetworkPolicy, ресурсні ліміти.
- TTS MCP: providers + Coqui fallback; voice mapping env vars (`ATLAS_TTS_AGENT_VOICE_*`).
- Falco → event stream → LLM3; LLM3 має audit trail і configurable auto-mitigation policy.

Тести: Falco event parsing, LLM3 decision logic, Playwright MCP scenario.

### MCP Hub — архітектура, контракти, метрики та авто-вибір

Архітектура:

- MCP Hub — це федерація контейнеризованих MCP-серверів (Playwright, Automation, macOS Automator, TTS/STT, FS/Git/HTTP тощо), до яких LLM2 підключається як клієнт.
- Дисквері: через env `ATLAS_MCP_SERVERS` і парні `ATLAS_MCP_<NAME>_URL`/`_HOST`/`_PORT`.
- Протоколи: HTTP/WebSocket; аутентифікація — токени/ключі з Kubernetes Secrets.

Узагальнений контракт (HTTP):

- `GET /health` → `{ status: "ok" }`
- `GET /capabilities` → список дій/інструментів MCP із схемами параметрів
- `POST /execute` `{ action, args, correlation_id }` → `{ status, result, metrics }`
- Телеметрія: Prometheus `/metrics` з лічильниками і гістограмами.

Ключові метрики (Prometheus):

- `mcp_request_total{mcp_name,action,success}` — лічильник успішних/помилкових викликів
- `mcp_request_latency_ms_bucket{mcp_name,action}` — гістограма затримок
- `mcp_error_total{mcp_name,error_code}` — помилки по кодах
- `mcp_selection_decision_total{intent,mcp_name,selected}` — рішення авто-вибору

Політика авто-вибору MCP:

- Для кожного intent/типу задачі обчислюється score = f(success_rate, p95_latency, останні відмови, cost_hint).
- За замовчуванням обирається інструмент з максимальним score; фолбек — другий за рейтингом.
- Порогові правила: якщо `success_rate < 0.8` або `p95_latency > 3000ms` — інструмент тимчасово знижується у пріоритеті (cooldown).

TTS/STT інтеграція (MCP TTS/STT):

- Підтримка провайдерів TTS: say/openai/elevenlabs/google/coqui (через локальний Coqui server).
- Прив'язка голосів до агентів: `ATLAS_TTS_AGENT_VOICE_LLM1/2/3`.
- STT провайдери: whisper/google/deepgram/vosk; мова через `ATLAS_STT_LANGUAGE`.

Безпека:

- NetworkPolicy: лише LLM2 може звертатись до MCP pod-ів; TTS/STT можуть робити вихідні запити лише до дозволених хостів.
- RBAC: кожен MCP має окремий ServiceAccount з мінімальними дозволами.

### Фаза 4 — Agent Registry, Dynamic Teams, UI (TEAM-01..TEAM-05, UI-01)

Ціль: створити реєстр агентів, конструктор команд, minimal UI та метрики команд.

Кроки: CRUD Agent Registry, YAML templates для ролей, AutoGen/MetaGPT integration для team construction з human-in-the-loop.

#### UI-01 — Мінімалістична перша сторінка (hacker theme) з 3D‑головою Atlas

Мета: одна публічна сторінка для користувача у стилі «хакерського термінала» (темний/неон),
із центровою 3D‑головою Atlas та базовим TTS‑озвученням.
Адмін‑панель прихована (доступ лише вибраним, у межах майбутнього UI).

Де тимчасовий код лежить зараз:

- Сервер демо: `tests/head-3d-server.js` (порт за замовчуванням `8099`).
  Це мінімальний standalone‑сервер (Express) для видачі статичних файлів та TTS‑проксі.
- Статика для 3D‑ресурсів: за логікою сервера, підхоплюється з `frontend/public`
  (якщо каталогу немає — створіть). Резервний шлях: `archive/frontend-face/public`.
- Корінь демо‑сторінки: `standalone/head-3d/` (сервер очікує тут `index.html`; створіть мінімальний файл при потребі).

3D‑модель (GLB) — тимчасове розміщення і параметризація шляху:

- Фронтенд сам визначає структуру та компонування. Нижче лише місця елементів і
  тимчасові шляхи — вони можуть бути змінені у будь‑який момент.
- Рекомендується параметризувати шлях до моделі (наприклад, `HEAD_MODEL_URL`)
  і підставляти його у коді рендера голови. Якщо змінюється місце зберігання
  моделі, необхідно оновити це посилання у клієнтському коді.
- За замовчуванням сервер віддає статичні файли з `frontend/public/` і
  мапить їх на `/assets/...`. Тимчасовий варіант — покласти GLB у
  `frontend/public/models/robot-head/` і звертатися як
  `/assets/models/robot-head/<your-model>.glb`.
- У продакшені шлях та спосіб доставки моделі можуть відрізнятися (CDN, інша
  структура папок тощо).

Варіанти інтеграції моделі (оберіть під свій сценарій):

1) Клієнтський файл (рекомендовано для MVP):
   - Додайте `<input type="file" accept=".glb,.gltf" />` і завантажуйте модель
     безпосередньо в рендерер (без фіксованих URL).
   - Переваги: немає залежності від серверного розміщення; простий DEMO.
   - Недолік: користувач має надати файл.

2) Центральний серверний рендер (headless/WebGL offscreen) з трансляцією
   зображення/кадру на клієнт:
   - Сервер малює сцену та віддає зображення/потік (наприклад, `<img>`/`<canvas>`
     з оновленням), клієнт показує готову картинку.
   - Переваги: передбачуваний фронт для користувача, централізований контроль.
   - Недолік: складніше інфраструктурно, вимоги до GPU/CPU.

У будь‑якому варіанті забезпечте на фронті «обличчя» для користувача: або
повноцінний 3D‑рендер, або fallback‑картинку (`public/hero.png`) на час
ініціалізації чи помилок.

Оточення та TTS (для демо):

- Сервер надає `/config.js` (DEV‑тільки) та `/tts` проксі для зменшення rate‑limit на клієнті.
- Ключі для TTS: задайте один із `GEMINI_API_KEY` або `GOOGLE_API_KEY` (або `GENAI_API_KEY`)
  у `.env` чи `config/environment.env` (цей файл сервер підхоплює автоматично, якщо існує).
  У продакшені не віддавайте ключі у браузер.

Мінімальна композиція першої сторінки (скетч‑структура):

- Фон — чорний, моноширинний шрифт, неонові акценти (зелений).
- По центру — 3D‑голова робота (GLB), «око» та елементи корпусу підсвічені.
- Зліва — «SMART_CHAT_SYSTEM»:
  - заголовок + кнопка ATLAS,
  - історія повідомлень,
  - поле вводу,
  - керування: Send, Mic, перемикачі режимів.
- Праворуч — `SERVER_LOGS` з фільтром та мітками рівнів (INFO/WARN/ERROR).
- Унизу — статус‑бар з індикаторами (зелена/червона крапка + підпис сервісу).

Орієнтовні блоки DOM (для фронтенду):

```html
<div class="main-bg">
  <div class="chat-panel">
    <div class="chat-header">SMART_CHAT_SYSTEM <button>ATLAS</button></div>
    <div class="chat-history">...</div>
    <div class="chat-input">...</div>
    <div class="chat-controls">[Atlas][TTS][Mic][Send][Console]</div>
  </div>
  <div class="head-3d-center"> <!-- канвас/вьюха з 3D‑моделлю --> </div>
  <div class="server-logs-panel">
    <div class="logs-header">SERVER_LOGS [filter]</div>
    <div class="logs-list">...</div>
  </div>
  <div class="status-bar">● MCP Hub ● LLM1 ● LLM2 ● LLM3 ● Registry ● TTS</div>
  <!-- Адмін‑панель прихована; доступна лише для вибраних користувачів у майбутньому UI -->
  <!-- ... -->
</div>
```

Як запустити демо (DEV):

1) Підготуйте залежності Node (Express/CORS/Dotenv). Якщо у корені немає їх у `package.json`, встановіть локально для демо:
   - `express`, `cors`, `dotenv` (версії не критичні для MVP).
2) Оберіть спосіб підключення моделі:
   - Клієнтський файл: додайте `<input type="file" ...>` і завантажуйте модель у рендерер.
   - Статичний шлях: тимчасово покладіть GLB у
  `frontend/public/models/robot-head/` та звертайтесь як
     `/assets/models/robot-head/<your-model>.glb`.
   - Параметризований URL: прокиньте змінну (напр., `HEAD_MODEL_URL`) через конфіг
     і використовуйте її у коді рендера голови.
3) За потреби створіть `standalone/head-3d/index.html` з контейнером та підключенням
   вашого клієнтського рендера 3D (three.js / React‑three‑fiber).
4) Запустіть сервер: Node.js ≥ 20, файл `tests/head-3d-server.js` (порт `8099`).
5) Відкрийте:
   - Сторінка: `http://localhost:8099/`
   - Health: `http://localhost:8099/health`
   - (Опційно) Шлях до моделі, якщо використовуєте статичний варіант: наприклад,
     `http://localhost:8099/assets/models/robot-head/<your-model>.glb`

Примітки безпеки:

- Ендпойнт `/config.js` віддає ключі у клієнт — використовуйте лише у DEV.
- Для продакшену передбачте: закриття адмін‑панелі, автентифікацію (JWT/OAuth),
  NetworkPolicy/Ingress ACL, вимкнення видачі ключів у браузер,
  TTS через безпечний бекенд.

#### Реєстр агентів (Team Registry) і Конструктор команд (Constructor) — деталі

Сховище даних:

- Формат: JSON/YAML файл або БД. За замовчуванням шлях у файлі: `ATLAS_AGENT_REGISTRY_PATH` (наприклад `./atlas/agents/registry.json`).
- Шаблони ролей/персон: YAML у каталозі `ATLAS_ROLE_TEMPLATES_PATH` (наприклад `./atlas/agents/roles/`).

Мінімальні схеми:

- Registry JSON:

```json
{
  "agents": [
    {
      "name": "Олег",
      "provider": "openai",
      "model": "gpt-4o-mini",
      "apiKeyRef": "OPENAI_API_KEY",
      "skills": ["coding", "planning"],
      "tools": ["playwright", "git", "tts"]
    }
  ],
  "teams": [
    {
      "name": "base-static",
      "members": ["Олег", "Ірина", "Марк"],
      "roles": {"Олег": "Lead", "Ірина": "Coder", "Марк": "Reviewer"}
    }
  ]
}
```

- Role template (YAML):

```yaml
name: Coder
persona: доброзичливий, структурований, слідує TDD
responsibilities:
  - написання коду за планом
  - створення юніт-тестів
guardrails:
  cost_limit_usd: 2.0
  max_calls: 50
tools: [git, playwright]
llm:
  provider: openai
  model: gpt-4o-mini
```

CRUD API (узагальнено):

- `POST /agents` `{ name, provider, model, apiKeyRef|apiKey, skills?, tools? }` → `{ id }`
- `GET /agents/:id` → `{ ... }` | `PATCH /agents/:id` → `{ ... }` | `DELETE /agents/:id`
- `POST /teams` `{ name, members[], strategy: static|dynamic, roleTemplates? }` → `{ id }`
- `POST /team/build` `{ taskId, constraints? }` → `{ teamId, members: [{name, role}] }`
- `POST /team/approve` `{ teamId, changes? }` → `{ status }`

Dynamic Team flow:

1) Завдання → визначення intent і домену.
2) Підбір ролей за шаблонами та відповідних агентів із реєстру.
3) Human-in-the-loop: підтвердження/правки.
4) Запуск AutoGen/MetaGPT з дозволеними MCP-інструментами.

### Фаза 5 — Production readiness, Final testing

Ціль: стабілізація, повні E2E, runbooks, DR/backup, SLOs/alerts, документи для операцій.


## Практичні малі приклади і артефакти

### Kompose — швидкий приклад та чек-лист ручних правок

```bash
# з корня репо
kompose convert -f compose.yaml -o infra/k8s/kompose-generated/
```

Після цього вручну:

- замінити Deployments баз даних на StatefulSet;
- додати `volumeClaimTemplates`;
- додати probes, resources, anti-affinity;
- видалити зайві ConfigMaps/Secrets, які містять секрети в тексті;
- зафіксувати зміни у `infra/k8s/manual/`.

### Falco подія — приклад JSON, який надходить до LLM3

```json
{
  "time": "2025-08-22T12:34:56.789Z",
  "rule": "Write below etc",
  "priority": "CRITICAL",
  "output": "Detected write to /etc/passwd",
  "source": "falco",
  "proc": { "pid": 1234, "cmdline": "/bin/sh -c echo bad > /etc/passwd" },
  "k8s": { "pod_name": "attacker-abc", "namespace": "default", "container_id": "docker://..." }
}
```

LLM3 реакція (псевдокод):

```text
1) receive_event(falco_event)
2) classify = llm3.classify(event)
3) if classify.severity >= CRITICAL:
   propose_action = llm3.suggest_actions(event)
   log.audit(event, propose_action)
   if policy.auto_mitigation_allowed(event):
     k8s.cordon_node(node)
     k8s.delete_pod(pod)
   else:
     human.notify_for_approval(propose_action)
```

### Orkes / workflow hint

- Для довготривалих робочих процесів використовувати Orkes/Conductor-подібний движок.
- Зберігати дефініції workflow у `infra/workflows/` (JSON/YAML).

## ADR (Architecture Decision Record)

Шлях: `docs/adr/`.

Шаблон ADR (зразок файлу `docs/adr/0001-llm2-ollama.md`):

```text
Title: LLM2 uses local Ollama by default
Status: accepted
Context: LLM2 orchestrator must work offline and avoid external model costs.
Decision: Use Ollama `gpt-oss:latest` for LLM2; allow fallback only when `ATLAS_LLM2_ALLOW_FALLBACK=true` and audit logs are recorded.
Consequences: + offline capability, - larger local infra requirements, need for healthchecks and model updates process.
Date: 2025-08-22
```

## Secrets, конфігурація і management

- Не зберігайте секрети в репозиторії. Шаблон змінних у `.env.example`.
- Для CI: використовуйте GitHub Actions Secrets та зчитуйте їх у runtime.
- У Kubernetes: зберігати секрети як
  `kubectl create secret generic ... --from-literal` або через
  sealed-secrets/HashiCorp Vault для production.

Рекомендовані env-перемінні (приклади в `.env.example`):

- `ATLAS_QLDB_URL`, `QDRANT_API_KEY`
- `ATLAS_LLM2_ALLOW_FALLBACK=false`
- `ATLAS_MCP_SERVERS` (наприклад `http://mcp-registry:8080`)

## Logging та Audit

- Всі агентські рішення (LLM2/LLM3) мають писатися в audit-log (structured JSON)
  з полями: timestamp, agent, input, decision, action, confidence, trace_id.
- Логи експортувати в centralized logging (ELK/Opensearch/CloudWatch). Для локального MVP — файли + stdout(Structured JSON).

Приклад поля audit:

```json
{
  "ts": "2025-08-22T12:00:00Z",
  "agent": "llm3",
  "event": "falco_detect",
  "decision": "cordon_node",
  "confidence": 0.93,
  "trace_id": "abc-123"
}
```

## DR / Backup

- Vector DB (Qdrant/Milvus): регулярні full/partial дампи; зберігати на object storage (S3).
- Redis: RDB/AOF snapshots + replication; тестувати recovery procedure у CI.
- Документувати recovery steps у `docs/runbooks/restore-from-backup.md`.

## SLOs & Alerts

- Приклади SLOs:
  - API availability: 99.9% (monthly)
  - RAG query p99 latency < 300ms

- Alerts (Prometheus Alertmanager):
  - Instance down
  - High error rate (>5% за 5 хв)
  - Qdrant replication lag

## CI skeleton (рекомендований набір кроків для GitHub Actions)

- lint: python/ts + kubeval for infra
- unit tests
- build images
- integration tests (kind) — optional/run-on-merge
- e2e tests — nightly or on-demand

Простий приклад workflow (опис):

1) Trigger: push/PR
2) Steps: checkout, setup Python/Node, run linters, run unit tests, kubeval on `infra/k8s/`.

## Runbook template (docs/runbooks/incident-\<id>.md)

```text
Title: <incident title>
Severity: P0 | P1 | P2
Symptoms: <what users see>
Detection: <alert/metric>
Mitigation: <short steps to mitigate>
Root cause: <investigation notes>
Postmortem: <link>
```

## Artifact paths (where to store generated artifacts)

- K8s manifests: `infra/k8s/` (kompose-generated + manual)
- Grafana dashboards: `infra/monitoring/grafana/initial-dashboard.json`
- Workflows: `infra/workflows/` (orkes definitions)
- ADRs: `docs/adr/`
- Runbooks: `docs/runbooks/`

## How to validate the document and next steps

1. Запустити markdownlint або `markdownlint-cli` для перевірки стилю документації.
2. Запустити `kubeval` для `infra/k8s/**/*.yaml`.
3. Далі: згенерувати початкові manifests з `kompose` і вручну доопрацювати critical items (StatefulSet, PVCs, probes).

---

Файл оновлено: цей `instruction.md` має бути позиційним для роботи — якщо потрібно, я можу:

- згенерувати початкові `infra/k8s/` маніфести з `kompose` та додати `infra/k8s/manual/` з виправленнями;
- створити `docs/adr/0001-llm2-ollama.md` та `docs/runbooks/restore-from-backup.md`;
- створити базовий GitHub Actions workflow файл `/.github/workflows/ci.yml`.

### Фаза 2: Agent MVP (Ключова функціональність агентів)

#### 2. Цілі та завдання

- **Ціль:** Реалізувати ключові функції агентів LLM1 (пам'ять) та LLM2 (оркестрація), створивши основу для виконання завдань.
- **Очікувані результати:** LLM1 може запам'ятовувати контекст,
  а LLM2 — декомпозувати завдання та використовувати інструмент `Linear`.

#### 3. Конкретні вимоги

- **MEM-01:** Реалізувати RAG-шар для LLM1.
  - Створити логіку індексації важливих фрагментів діалогу в Qdrant/Milvus.
  - Реалізувати логіку пошуку релевантних "спогадів" та додавання їх до промпту.
- **ORC-01:** Налаштувати LLM2.
  - Підняти локальний сервер Ollama з моделлю `gpt-oss:latest`.
  - Інтегрувати фреймворк AutoGen/MetaGPT для керування агентом.
  - Створити інструмент (tool) для роботи з Linear GraphQL API (створення та оновлення завдань).
- **CFG-01:** Створити абстракцію для LLM-провайдерів (OpenAI, Mistral, Gemini, Ollama)
  з єдиним інтерфейсом для LLM1 та LLM3. Реалізувати логіку фолбек-ланцюга.
- **CFG-02:** Жорстко прив'язати LLM2 до локальної Ollama. Реалізувати healthcheck та
  механізм контрольованого фолбеку (лише якщо `ATLAS_LLM2_ALLOW_FALLBACK=true`).

#### 4. Тестування та CI/CD

- **Unit-тести:**
  - Тести для RAG-шару: індексація, пошук, форматування контексту.
  - Тести для обгортки Linear API.
  - Тести для абстракції LLM-провайдерів та логіки фолбеку.
- **Інтеграційні тести:**
  - LLM1 отримує діалог, зберігає його в Qdrant, і при наступному запиті витягує релевантний контекст.
  - LLM2 отримує завдання, і через AutoGen успішно викликає інструмент Linear, що створює реальний issue.
- **E2E-тести:**
  - Повний цикл: користувач ставить завдання LLM1 → LLM1 формалізує його →
    LLM2 отримує завдання, декомпозує його та створює issue в Linear.
    Перевірити, що issue створено з правильними даними.
- **CI/CD:**
  - Додати всі нові unit та інтеграційні тести в існуючий workflow.
  - Запускати E2E-тести (можливо, з моком Linear API або в тестовому проекті Linear) в рамках CI.

---

### Фаза 3: Автоматизація та Безпека

#### 2. Цілі та завдання

- **Ціль:** Інтегрувати систему моніторингу безпеки (LLM3 + Falco) та реалізувати безпечне виконання
  браузерної автоматизації.
- **Очікувані результати:** Система реагує на загрози безпеки та може виконувати завдання в браузері в
  ізольованому середовищі.

#### 3. Конкретні вимоги

- **SEC-01:** Інтегрувати LLM3 з Falco.
  - Розгорнути Falco в K8s-кластері.
  - Налаштувати потік подій з Falco до LLM3.
  - Реалізувати в LLM3 логіку класифікації подій та прийняття рішень.
  - Додати мінімум дві автоматизовані реакції (напр., `cordon node`, `delete pod`) через Kubernetes API.
- **GUI-01:** Налаштувати безпечний запуск Playwright.
  - Використовувати ізольований контейнер (Apple container, Kasm, або аналог) для запуску браузера.
- **MCP-01 (частково):** Створити та розгорнути `Playwright MCP` сервер,
  який буде приймати завдання від LLM2 і виконувати їх у безпечному середовищі.

#### 4. Тестування та CI/CD

- **Unit-тести:**
  - Тести для логіки парсингу та класифікації подій Falco в LLM3.
- **Інтеграційні тести:**
  - Згенерувати тестову подію Falco та перевірити, що LLM3 її отримує, правильно класифікує та викликає
    відповідний метод для реакції (можна мокати K8s API).
  - LLM2 відправляє завдання на `Playwright MCP`, і той успішно виконує простий сценарій (відкрити сторінку,
    зробити скріншот).

- **E2E-тести:**
  - Згенерувати реальну подію безпеки в кластері (напр., запуск shell у контейнері) → Falco її фіксує → LLM3 реагує
    (напр., ізолює pod через NetworkPolicy) → дія та причина логуються.
- **Тести безпеки:**
  - Перевірити, що контейнер з Playwright дійсно ізольований і не має доступу до хостової системи чи інших pod'ів, крім дозволених.
- **CI/CD:**
  - Додати всі нові тести у воркфлоу. Запускати тести безпеки на регулярній основі.

---

## Безпека — політики LLM3 і матриця Falco→реакції

Приклад матриці відповідей LLM3 на події Falco (первинний набір):

| Тип події | Falco правило | Рівень | Авто-реакція LLM3 | Обґрунтування |
|---|---|---|---|---|
| Зміна системних файлів | Write below etc | CRITICAL | cordon_node + delete_pod | Локалізація та зупинка потенційної ескалації привілеїв |
| Shell усередині контейнера | Terminal shell in container | HIGH | apply NetworkPolicy (isolate pod) | Стримування lateral movement, збір артефактів |
| Підозрілі вихідні з’єднання | Unexpected outbound connection | HIGH | deny egress via NetworkPolicy | Блокування ексфільтрації |
| Масове читання секретів | Read sensitive file untrusted | CRITICAL | revoke secret + rotate | Мінімізація витоку даних |
| Високе використання CPU | Container CPU hog | MEDIUM | notify + scale check | Спершу спостереження/людське підтвердження |

Примітки:

- Для CRITICAL дозволена авто-мітігація без підтвердження, якщо `policy.auto_mitigation_allowed(event)==true`.
- Всі дії журналюються: `timestamp, event, decision, reasoning, trace_id, approval_status`.

Політика ізоляції компонентів (Playwright/Kasm/Apple container):

- Окремий namespace (наприклад `automation`).
- `NetworkPolicy`: дозволити ingress лише з LLM2; egress — лише до призначених доменів/портів.
- Ліміти ресурсів (рекомендації стартові): `cpu: 500m–2`, `memory: 512Mi–4Gi` залежно від сценаріїв.
- SecurityContext: `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`.
- Для Apple container/Kasm: VM-рівень ізоляції або sandbox-профілі; заборонити доступ до хоста/сокетів Docker.

Приклад NetworkPolicy для MCP серверів (дозвіл лише від LLM2):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-llm2-to-mcp
  namespace: automation
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: llm2
    ports:
    - protocol: TCP
      port: 4000
  policyTypes: [Ingress]
```

Приклад ресурсних лімітів у Deployment:

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2"
    memory: "4Gi"
```

## Kubernetes маніфести — мінімальні приклади

StatefulSet для Qdrant/Milvus (уривок):

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
spec:
  serviceName: qdrant
  replicas: 1
  selector:
    matchLabels: { app: qdrant }
  template:
    metadata:
      labels: { app: qdrant }
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports: [{ containerPort: 6333 }]
        volumeMounts:
        - name: data
          mountPath: /qdrant/storage
        readinessProbe: { httpGet: { path: /, port: 6333 }, initialDelaySeconds: 5, periodSeconds: 10 }
        livenessProbe: { httpGet: { path: /, port: 6333 }, initialDelaySeconds: 15, periodSeconds: 20 }
        resources:
          requests: { cpu: "500m", memory: "1Gi" }
          limits: { cpu: "2", memory: "4Gi" }
  volumeClaimTemplates:
  - metadata: { name: data }
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 50Gi
```

Deployment для LLM-агента (уривок):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm2
spec:
  replicas: 1
  selector: { matchLabels: { app: llm2 } }
  template:
    metadata: { labels: { app: llm2 } }
    spec:
      containers:
      - name: llm2
        image: yourorg/llm2:latest
        env:
        - name: OLLAMA_BASE_URL
          value: http://ollama:11434
        - name: ATLAS_LLM2_ALLOW_FALLBACK
          value: "false"
        readinessProbe: { httpGet: { path: /health, port: 8080 } }
        livenessProbe: { httpGet: { path: /health, port: 8080 }, initialDelaySeconds: 15 }
        resources:
          requests: { cpu: "500m", memory: "1Gi" }
          limits: { cpu: "2", memory: "4Gi" }
```

NetworkPolicy для ізоляції MCP — див. вище.

## Конфігурація та приклади .env

Доданий приклад `.env.example` у корені репозиторію. Ключові групи змінних:

- LLM1/2/3: `ATLAS_LLM{1,2,3}_PROVIDER`, `ATLAS_LLM{1,2,3}_MODEL`, `ATLAS_LLM{1,2,3}_FALLBACKS`,
  `ATLAS_LLM2_ALLOW_FALLBACK`, `ATLAS_LLM_TIMEOUT_MS`, `OLLAMA_BASE_URL`.
- Пам'ять/дані: `QDRANT_URL`, `QDRANT_API_KEY` або `MILVUS_ENDPOINT`, `REDIS_URL`.
- MCP Hub: `ATLAS_MCP_SERVERS`, `ATLAS_MCP_<NAME>_URL`, `ATLAS_MCP_<NAME>_ENABLED`.
- TTS/STT: `ATLAS_TTS_PROVIDERS`, `ATLAS_TTS_AGENT_VOICE_LLM1/2/3`, `COQUI_TTS_BASE_URL`, `ATLAS_STT_PROVIDER`, `ATLAS_STT_LANGUAGE`.
- Інтеграції: `LINEAR_API_KEY`, `ORKES_BASE_URL`, `ORKES_API_KEY`.
- Провайдери: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MISTRAL_API_KEY`, `GOOGLE_API_KEY`.

## Тестові сценарії і критерії приймання — конкретика

Фаза 1 (інфраструктура):

- Персистентність: створити колекцію у Qdrant → перезапустити pod → перевірити наявність даних (очікувано: OK).
- Моніторинг: Prometheus збирає метрики з `mcp-*` і `llm*` сервісів; Grafana відображає дашборд (без помилок запитів).

Фаза 2 (RAG/LLM1, LLM2/Ollama):

- RAG: індексувати 3 фрагменти, запитати пов'язаний контент — очікувати, що top‑k містить щонайменше 2 релевантні фрагменти.
- LLM2: healthcheck Ollama (`/api/tags`) повертає OK; створення issue в Linear повертає валідний `url`.

Фаза 3 (MCP/Falco/LLM3):

- Falco симуляція: відправити зразок події `Write below etc` → LLM3 приймає рішення `cordon_node|delete_pod` і пише audit‑запис.
- Playwright MCP: виконати `open+snapshot` сценарій — отримати збережений артефакт і запис у метриках.

Фаза 4 (Registry/Teams/TTS):

- CRUD: створити агента через API → отримати `id` → зчитати, оновити, видалити (успіх 200/204).
- TTS фолбек: вимкнути primary провайдера → очікувати успішне озвучення через Coqui і подію в метриках `fallback=1`.

E2E (повний потік):

- «Запит → LLM1 (RAG) → LLM2 (план + Linear)»: очікувати створене issue, аудити й трейс.

## Блок‑схеми (ASCII)

Потік даних (спрощено):

```text
[User] -> [LLM1 (RAG)] -> [LLM2 Orchestrator] -> [MCP Hub tools]
                                  |                ^
                                  v                |
                              [Linear API]     [Prometheus]

[Falco] -> [LLM3 Security] -> [K8s Actions] -> [Audit/Logs]
```

Формування команди:

```text
Task -> Intent -> Role Templates -> Match Agents -> Human Approve -> Run (AutoGen)
```

Алгоритм LLM3 на подію Falco (узагальнено):

```text
Event -> Classify(severity) -> Propose actions -> Audit ->
  if AutoPolicy OK: Execute -> Record
  else: Request Approval -> Execute/Abort
```

## Моніторинг і алерти — приклади PromQL

- Успіх MCP: `sum(rate(mcp_request_total{success="true"}[5m])) by (mcp_name)`
- Помилки MCP: `sum(rate(mcp_request_total{success="false"}[5m])) by (mcp_name,action)`
- Затримка MCP p95: `histogram_quantile(0.95, sum(rate(mcp_request_latency_ms_bucket[5m])) by (le,mcp_name))`
- Відсоток фолбеків TTS: `sum(rate(mcp_selection_decision_total{selected="false"}[15m])) / sum(rate(mcp_selection_decision_total[15m]))`

Пороги алертів (рекомендація стартова):

- MCP error_rate > 5% за 5 хв — Warning; >10% — Critical
- MCP p95 latency > 3s за 10 хв — Warning
- Falco critical events > 0 протягом 1 хв — Page (P1)

## DR/Backup — план та періодичність

- Vector DB (Qdrant/Milvus): daily incremental, weekly full; зберігання на S3‑сумісному сховищі ≥30 днів.
- Redis: RDB кожні 15 хв або AOF; щоденний snapshot на зовнішнє сховище.
- Перевірка відновлення: щомісячне тренування у sandbox/CI — відновити копію БД і виконати пробні RAG‑запити.
- Runbook: див. `docs/runbooks/restore-from-backup.md` (оновлено інструкціями з періодичністю і валідацією).

## Глосарій

- MCP (Model Context Protocol): протокол взаємодії з інструментами/сервісами як «плагінами» для агентів.
- RAG (Retrieval‑Augmented Generation): пошук релевантних знань у векторному сховищі та додавання їх до промпту.
- AutoGen/MetaGPT: фреймворки для багатоагентної оркестрації та співпраці.
- Falco: рушій правил для безпеки контейнерів/ядра з потоками подій.
- Coqui TTS: локальний рушій синтезу мовлення.

## FAQ

Q: Чому LLM2 має бути локальним на Ollama?
A: Приватність/затримка/витрати. Віддалені провайдери допускаються лише як контрольований фолбек із аудитом.

Q: Чи обов'язковий Orkes?
A: Ні. Для довгих/стійких процесів рекомендовано; MCP покриває «інструменти», Orkes — «процеси».

Q: Де зберігати ключі?
A: У Kubernetes Secrets/CI secrets, не в коді/репозиторії. Шаблон у `.env.example` — лише для локальної розробки.

### Фаза 4: Команди, TTS та повний MCP Hub

#### 2. Цілі та завдання

- **Ціль:** Розгорнути платформу для динамічного створення команд агентів, додати голосові можливості (TTS) та
  повноцінний набір інструментів через MCP Hub.
- **Очікувані результати:** Система може формувати команди агентів під завдання, використовувати різні інструменти
  через MCP та озвучувати свої відповіді.

#### 3. Конкретні вимоги

- **MCP-01-04:** Розгорнути повний MCP Hub: Playwright, Automation, macOS Automator, Redis/Buffer, FS/Git/HTTP.
  Налаштувати реєстр через `ATLAS_MCP_SERVERS` та підключення з LLM2. Реалізувати політику авто-вибору MCP за
  метриками.
- **MCP-05-06:** Інтегрувати `TTS MCP` з усіма провайдерами (включно з локальним Coqui). Прив'язати голоси до агентів
  через env та налаштувати фолбек.
- **TEAM-01:** Реалізувати "Реєстр агентів" (CRUD, зберігання в JSON/YAML).
- **TEAM-02:** Створити шаблони ролей/персон (YAML) та логіку їх автоматичного призначення.
- **TEAM-03:** Реалізувати побудову динамічної команди через AutoGen/MetaGPT з обов'язковим підтвердженням від
  користувача ("human-in-the-loop").
- **TEAM-05:** Створити дашборд в Grafana для моніторингу ефективності команд та MCP-інструментів.

#### 4. Тестування та CI/CD

- **Unit-тести:**
  - Тести для CRUD-операцій Реєстру агентів.
  - Тести для логіки призначення ролей.
  - Тести для логіки фолбеку TTS-провайдерів.

- **Інтеграційні тести:**
  - Створити динамічну команду для тестового завдання, підтвердити її, і перевірити, що AutoGen розпочав виконання.
  - Запит на озвучення тексту успішно обробляється основним TTS-провайдером. Після його штучного відключення запит
    успішно обробляється наступним у ланцюжку (Coqui).
  - "Два MCP управління macOS": відправити однакове завдання на обидва MCP, перевірити, що метрики зібрані, і при
    повторному виклику обирається ефективніший.

- **E2E-тести:**
  - Користувач ставить комплексне завдання → система формує динамічну команду, отримує підтвердження → команда в процесі
    виконання використовує кілька інструментів з MCP Hub (напр., Git та Playwright) та озвучує проміжні результати через
    TTS.

- **CI/CD:**
  - Додати всі нові тести у воркфлоу.

---

### Фаза 5: Фронтенд та Фіналізація

#### 2. Цілі та завдання

- **Ціль:** Створити мінімальний, але повнофункціональний веб-інтерфейс для взаємодії з системою та провести
  фінальне тестування.
- **Очікувані результати:** Готовий до демонстрації продукт з веб-інтерфейсом, що пройшов повний цикл тестування.

#### 3. Конкретні вимоги

- **UI-01:** Після стабілізації бекенд-контрактів розробити мінімальний "реальний" веб-інтерфейс. Усі дії в UI мають
  працювати через існуючі API без моків чи симуляцій.
- **UI-02:** Написати E2E-тести для фронтенду (напр., за допомогою Playwright).
- **OBS-01 (фіналізація):** Створити всі дашборди в Grafana, що описані в `ATLAS.md`.

#### 4. Тестування та CI/CD

- **Unit-тести:**
  - Тести для UI-компонентів (напр., з Jest/React Testing Library).

- **Інтеграційні тести:**
  - Тести взаємодії UI з бекенд API (можна мокати API).
  - Повні сценарії користувача через UI: від входу та постановки задачі до моніторингу її виконання та перегляду
    результатів. Тести запускаються проти повністю розгорнутого "живого" середовища.

- **Тестування продуктивності:**
  - Базові тести навантаження на API та веб-інтерфейс.
  - Пройтися по всіх пунктах з розділу "Критерії приймання" в `ATLAS.md` і перевірити їх виконання.

- **CI/CD:**
  1. Збірка бекенду та фронтенду (Docker-образи).
  2. Unit-тести (бекенд/фронтенд).
  3. Інтеграційні тести (RAG/Linear).
  4. E2E-тести (повний цикл через UI).
  5. Розгортання в staging-середовище.
  6. (Опційно) Ручне або автоматичне розгортання в production.

---

## 4. Обмеження та Керівні принципи

### Технічні обмеження

- **Локальна Ollama для LLM2:** Строго використовувати локальну Ollama з моделлю `gpt-oss:latest`.
  Фолбек на віддалені провайдери лише з явним дозволом `ATLAS_LLM2_ALLOW_FALLBACK=true`.
- **Ізоляція браузера:** Playwright та інші GUI-автоматизації повинні виконуватися в ізольованих контейнерах
  (Apple container/Kasm) для безпеки.
- **Kubernetes-first:** Всі сервіси мають розгортатися в Kubernetes. Docker Compose використовується лише для первинної розробки.
- **Фронтенд останнім:** Веб-інтерфейс розробляється після стабілізації API. Ранні UI-прототипи мають бути повністю
  підключені до бекенду без моків.

### Стандарти кодування

- **Python:** Використовувати `black` для форматування, `ruff` для лінтингу, `pytest` для тестування.
- **TypeScript/JavaScript:** ESLint + Prettier для стилю, Jest/Vitest для unit-тестів.
- **Контейнери:** Multi-stage Dockerfile для оптимізації розміру образів.
- **K8s маніфести:** Використовувати `kubeval` або `kubeconform` для валідації.

### Патерни проектування

- **Dependency Injection:** Для управління залежностями між компонентами (особливо LLM-провайдери).
- **Strategy Pattern:** Для реалізації фолбек-ланцюгів LLM-провайдерів.
- **Circuit Breaker:** Для захисту від відмов зовнішніх сервісів (Ollama, Linear API).
- **Observer Pattern:** Для системи метрик та моніторингу MCP-інструментів.

### Міркування щодо продуктивності

- **RAG-пошук:** Обмежувати результати до топ-5 релевантних спогадів для контролю розміру контексту.
- **MCP-підключення:** Використовувати connection pooling та keep-alive для підключень до MCP-серверів.
- **Prometheus метрики:** Обмежувати кардинальність лейблів (максимум 10 значень на лейбл).

### Вимоги безпеки

- **Secrets:** Всі API-ключі та паролі зберігати в Kubernetes Secrets, ніколи в коді.
- **RBAC:** Мінімальні дозволи для кожного сервісу (принцип найменших привілеїв).
- **NetworkPolicy:** Обмежувати мережевий трафік між pod'ами за білим списком.
- **Аудит:** Всі дії LLM3 (реакції на події Falco) мають логуватися для розслідування.

---

## 5. Переваги форматування

### Мови програмування

- **Backend:** Python 3.11+ з FastAPI для HTTP API
- **Frontend:** TypeScript з React або Vue.js (на вибір після стабілізації API)
- **Інфраструктура:** YAML для K8s маніфестів, Bash/Python для скриптів автоматизації
- **Конфігурація:** YAML для ролей агентів, JSON для реєстру агентів

### Структура коду

---
---
<!-- Removed duplicate overview block to avoid lint issues and keep single canonical plan above -->

## 1. Контекст і архітектурна картина

- Проєкт: ATLAS — багатоагентна система з трьома базовими LLM-агентами:
  - LLM1 — користувацький інтерфейс і довготривала пам'ять (RAG).
  - LLM2 — локальний оркестратор/оркестраційний агент (повинен використовувати Ollama: gpt-oss:latest за замовчуванням).
  - LLM3 — агент безпеки і нагляду, підключений до Falco.
- Інструментальна шина: MCP Hub — набір контейнеризованих сервісів (Playwright, TTS, Automation,
  macOS Automator та ін.), які агенти можуть викликати.
- Платформа оркестрації: Kubernetes — декларативний підхід, маніфести в `k8s/`.

## 2. Фази реалізації — детально

### Фаза 1 — Інфраструктура (INF-01, INF-02, OBS-01, OPS-01)

Ціль: Побудувати стабільну інфраструктуру K8s з персистентними сховищами та базовим моніторингом.

Кроки:

1. Створити `k8s/` каталог і конвертувати `compose.yaml` через Kompose як початкову точку.

1. Ручне доопрацювання згенерованих манифестів:

- StatefulSet для Qdrant/Milvus і Redis з `volumeClaimTemplates`.
- Deployment для stateless сервісів (агенти, API, MCP-клієнти).
- Readiness & Liveness probes для сервісів.
- Resource requests/limits для всіх pod'ів.
- Anti-affinity / podAntiAffinity для критичних сервісів.

1. Storage:

- Додати StorageClass (локальний або cloud) і PVC-політики.
- Документувати правила бекапу томів.

1. Моніторинг:

- Розгорнути Prometheus + Grafana в namespace `observability`.
- Налаштувати ServiceMonitors або Prometheus scrape targets для всіх сервісів.
- Експортувати початкові dashboard JSON для Grafana у `infra/monitoring/`.

1. Сек'юриті та операції:

- Створити Kubernetes Secrets для всіх ключів (з `.env.example` як шаблоном).
- Налаштувати мінімальні RBAC ролі для сервісних акаунтів (`principle of least privilege`).
- Впровадити базові NetworkPolicy для розмежування трафіку.

Тести і CI:

- Лінт манифестів (`kubeval`/`kubeconform`).
- Інтеграційний pipeline: optional `kind`-кластер у CI; розгортання манифестів → smoke tests (svc reachable) → teardown.
- Скрипти перевірки персистентності (запис → delete pod → перевірка даних).

Критерії приймання:

- PVC працюють і зберігають дані після рестарту.
- Prometheus збирає метрики; Grafana відображає мінімальні панелі.
- Secrets прописані і не коммітяться в репо.

### Фаза 2 — Core agents і RAG (MEM-01, CFG-01, CFG-02, ORC-01)

Ціль: Реалізувати RAG для LLM1 і локальний оркестратор LLM2 з AutoGen/MetaGPT та інтеграцією Linear.

Компоненти та контракти:

- RAG-шар:
  - Входи: текст/доки (user messages), параметри chunking.
  - Виходи: набір релевантних фрагментів (top-k), embed vectors stored in Qdrant/Milvus.
  - Error modes: DB недоступна, ембедінг провайдер паде — fallback на локальний кеш або повернення короткого контексту.
  - Success: релевантні фрагменти додаються до prompt LLM1.

- SemCache (Redis):
  - Кеш семантично подібних запитів; TTL за політикою; контроль порогу схожості.

- LLM Provider Abstraction:
  - Уніфікований інтерфейс для OpenAI, Mistral, Gemini, Ollama.
  - Фолбек-ланцюг configurable; для LLM2 фолбек дозволений тільки коли ATLAS_LLM2_ALLOW_FALLBACK=true.

LLM2 (оркестратор):

- Запуск локальної Ollama інстанції з моделлю `gpt-oss:latest`.
- Healthcheck endpoint та журналування відмов (audit log при фолбеку).
- Інструмент Linear tool: GraphQL client, retry/circuit-breaker, unit тестований.

Тести:

- Unit: chunking, embedding pipe, qdrant index/store/retrieve; provider chain unit tests.
- Integration: LLM1 ↔ RAG retrieval; LLM2 ↔ Ollama; Linear tool creating issues in test project.
- E2E: full flow user → LLM1 (RAG) → LLM2 (plan + Linear issue).

CI:

- Додавати тести в GitHub Actions; mock external APIs where needed for CI stability.

### Фаза 3 — MCP Hub, Automation і Безпека (MCP-01..MCP-06, SEC-01, GUI-01)

Ціль: Створити MCP Hub, ізольований виконувальний шар для браузерної автоматизації,
та LLM3 інтеграцію з Falco для активного реагування.

Kroky:

- MCP Hub:
  - Реєстр доступних MCP серверів через env `ATLAS_MCP_SERVERS` або Service Discovery.
  - Контракты: HTTP/gRPC endpoints, auth tokens, timeouts, rate limits.
  - Метрики: latency, success_rate, error_rate — експортувати в Prometheus.
- Playwright MCP:
  - Виконувати сценарії в ізольованих контейнерах; обмежити мережеві політики та ресурси; mount тільки потрібні артефакти.
- TTS MCP:
  - Підтримка кількох провайдерів (OpenAI, Google, ElevenLabs) з локальним Coqui fallback.
  - Voice mapping env vars: `ATLAS_TTS_AGENT_VOICE_LLM1`, `ATLAS_TTS_AGENT_VOICE_LLM2`, `ATLAS_TTS_AGENT_VOICE_LLM3`.
- macOS Automation MCPs:
  - Два типи: Automation MCP та macOS Automator MCP — реалізувати telemetry export і безпечні інтерфейси.

LLM3 & Falco:

- Розгортання Falco; piping подій до LLM3 (streaming, webhooks або message bus).
- LLM3 аналізує події, оцінює ризик, пропонує або виконує (за політикою) автоматизовані дії через K8s API:
  cordon, drain, delete pod, revoke secret.
- Жорсткі правила: автоматичні дії мають audit trail і approval gates для чутливих операцій.

Тести:

- Unit: Falco event parsing, TTS fallback logic, MCP selection policy.
- Integration: simulate Falco event → LLM3 reaction (mock K8s); LLM2 → Playwright MCP scenario.
- E2E: user requests screenshot → LLM2 uses Playwright MCP → result saved + TTS reads result.

### Фаза 4 — Agent Registry, Dynamic Teams і UI (TEAM-01..TEAM-05, UI-01)

Ціль: Дати змогу динамічно збирати команди агентів, керувати ними і додати голосовий інтерфейс та мінімальний фронтенд.

Компоненти:

#### Agent Registry

- **CRUD API**: зберігання конфігурацій агентів, ролей, секретів (посилання на K8s Secrets), health status.
- **Шаблони ролей**: YAML-templates для різних типів агентів і персон.
- **Інтеграція з провайдерами**: безпечне зберігання API ключів через Kubernetes Secrets.

#### Dynamic Team Constructor

- **Аналіз завдань**: AutoGen/MetaGPT аналізує intent завдання і пропонує склад команди.
- **Автопризначення ролей**: система автоматично призначає ролі агентам на основі їх навичок.
- **Human-in-the-loop gate**: обов'язкове підтвердження користувачем перед запуском команди.
- **Guardrails**: ліміти вартості/запитів, rate limiting, аудит дій команди.

#### TTS та STT інтеграція

- **TTS MCP**: підтримка кількох провайдерів (OpenAI, Google, ElevenLabs) з локальним Coqui fallback.
- **Voice mapping**: прив'язка унікальних голосів до агентів (`ATLAS_TTS_AGENT_VOICE_LLM1`, `..._LLM2`, `..._LLM3`).
- **STT MCP**: розпізнавання мовлення для участі користувача в Live Debate Mode.

#### Live Debate Mode

- **Режим живої дискусії**: агенти можуть вести голосову дискусію між собою.
- **Модерація**: механізми контролю та спрямування дискусії.
- **Підсумовування**: автоматичне підсумовування результатів дискусії.

#### Grafana dashboards

- Метрики команд: cost, duration, success_rate.
- TTS/STT usage metrics та fallback events.
- MCP Hub performance та auto-selection metrics.

Тести:

- **Unit тести**: Registry CRUD, team assembly logic, TTS/STT fallback.
- **Integration тести**: Constructor + AutoGen orchestration, TTS з різними провайдерами.
- **E2E тести**: повний потік з TTS, MCP usage та Live Debate scenarios.

### Фаза 5 — Production readiness і Frontend

Ціль: Підготувати систему до production: повні E2E тести, документація, runbooks і мінімальний веб-інтерфейс.

Кроки:

- Frontend: після стабілізації API зробити lightweight UI (React/TS) підключений до бекенду, E2E тестований Playwright.
- CI: pipeline: build images, run unit+integration tests, deploy to staging, run E2E, promote.
- Ops: backup/restore procedure for vector DB and Redis; runbooks для реакції на інциденти.

Тести і приймання:

- Nightly full E2E suite, security scans, performance tests.

## 3. Контракти та технічні рішення (коротко)

- Формати даних, API contracts, env variables: тримати у /docs/openapi і `.env.example`.
- Storage: Qdrant/Milvus schema for embeddings, metadata fields (timestamp, source, conversation_id, chunk_id).
- Metrics: Prometheus metrics naming conventions and Grafana dashboard JSONs.

### Orkes integration (long-running workflows)

- When long-running workflows are needed (multi-step, durable), use Orkes/Conductor style orchestration.
- Contract: workflow definition (JSON/YAML) stored in `infra/workflows/`;
  tasks call services via HTTP/gRPC; state and task history persisted by Orkes.
- Tests: unit test workflow definitions (lint),
  integration test by running a sample workflow against a local Orkes instance in CI.

### Kompose quick example and manual refinements

- Convert compose to k8s YAML (local dev step):

```bash
# from repo root
kompose convert -f compose.yaml -o infra/k8s/kompose-generated/
```

- Manual refinement checklist after conversion:
  - Replace generated Deployments for databases with `StatefulSet` and add `volumeClaimTemplates`.
  - Add `readinessProbe` and `livenessProbe` for each service.
  - Add `resources.requests` and `resources.limits`.
  - Add `podAntiAffinity` to critical services.

### Falco event example and LLM3 pseudocode

- Example Falco event (JSON) delivered to LLM3 webhook/message queue:

```json
{
  "time": "2025-08-22T12:34:56.789Z",
  "rule": "Write below etc",
  "priority": "CRITICAL",
  "output": "Detected write to /etc/passwd",
  "source": "falco",
  "proc": { "pid": 1234, "cmdline": "/bin/sh -c echo bad > /etc/passwd" },
  "k8s": { "pod_name": "attacker-abc", "namespace": "default", "container_id": "docker://..." }
}
```

- LLM3 pseudocode reaction flow (simplified):

```text
1) receive_event(falco_event)
2) classify = llm3.classify(event)
3) if classify.severity >= CRITICAL:
     propose_action = llm3.suggest_actions(event)
     log.audit(event, propose_action)
     if policy.auto_mitigation_allowed(event):
         k8s.cordon_node(node)
         k8s.delete_pod(pod)
     else:
         human.notify_for_approval(propose_action)
```

### ADR (Architecture Decision Record) template

- Path: `docs/adr/` — keep one file per decision, e.g. `0001-llm2-ollama.md`.
- Minimal ADR template:

```text
Title: <short decision title>
Status: proposed | accepted | deprecated
Context: <why this decision is required>
Decision: <what you decided>
Consequences: <implications, trade-offs>
Date: YYYY-MM-DD
```

- Example ADR (LLM2 model):

```text
Title: LLM2 uses local Ollama by default
Status: accepted
Context: LLM2 orchestrator must work offline and avoid external model costs.
Decision: Use Ollama `gpt-oss:latest` for LLM2; allow fallback only when `ATLAS_LLM2_ALLOW_FALLBACK=true` and audit logs are recorded.
Consequences: + offline capability, - larger local infra requirements, need for healthchecks and model updates process.
Date: 2025-08-22
```

### Grafana dashboards export path

- Store exported dashboards in `infra/monitoring/grafana/initial-dashboard.json` and reference them in deployment
  manifests (ConfigMap or provisioning).


## 4. Тестування та CI/CD — рекомендації

- Unit coverage ≥ 80% для критичних компонентів.
- Integration tests run in CI on merge; E2E run nightly or on demand against staging.
- Use `kind` in CI for K8s integration tests; mock external APIs where necessary.

## 5. Стандарти кодування та патерни

- Python: black, ruff, pytest, typing.
- Node/TS: ESLint, Prettier, Jest/Playwright for E2E.
- Patterns: DI, Strategy, Circuit Breaker, Observer.

## 6. Структура репозиторія (рекомендована)

```text
atlas/
├── agents/
│   ├── llm1/
│   ├── llm2/
│   └── llm3/
├── mcp/
│   ├── servers/
│   └── client/
├── infra/
│   ├── k8s/
│   └── monitoring/
├── web/
│   └── ui/
├── scripts/
└── tests/
```

## 7. Приклади команд та швидкий старт (локально)

- Рекомендовані кроки для початку локальної роботи (референс):

1. Лінт манифестів та перевірка формату:

```bash
# Перевірити всі k8s yaml
kubeval infra/k8s/**/*.yaml
```

1. Локальний кластер (kind) для інтеграційних тестів:

```bash
kind create cluster --name atlas-test
kubectl apply -f infra/k8s/
# запустити smoke tests
```

1. Запуск unit тестів (Python):

```bash
python -m pytest -q
```

## 8. Питання для уточнення (якщо потрібно)

- Який Linear project треба використовувати у тестах?
- Чи є доступ до Apple Container, або використовуємо Kasm/другий варіант?
- Які провайдери TTS мають пріоритет?

## 9. Критерії приймання (Acceptance Criteria)

### LLM1 (Interface + Memory)

- **RAG функціональність**: LLM1 повертає відповідь із релевантними "спогадами" з векторної БД з атрибуцією джерела (логування).
- **Семантичний кеш**: Redis кешує семантично подібні запити, TTL працює коректно.
- **Provider fallback**: При недоступності основного LLM провайдера спрацьовує fallback chain.

### LLM2 (Orchestrator)

- **Ollama інтеграція**: LLM2 використовує локальну Ollama (`gpt-oss:latest`) за замовчуванням.
- **Linear інтеграція**: LLM2 викликає Linear API і повертає URL створеного issue.
- **Fallback control**: Фолбек на зовнішні провайдери працює тільки при `ATLAS_LLM2_ALLOW_FALLBACK=true` з аудит логуванням.
- **AutoGen/MetaGPT**: Успішна інтеграція з фреймворком для агентської оркестрації.

### LLM3 (Security & Monitoring)

- **Falco інтеграція**: LLM3 отримує події Falco і класифікує їх за рівнем ризику.
- **Автоматизовані реакції**: Виконує мінімум 2 автоматичні дії (cordon node, delete pod) через Kubernetes API.
- **Audit trail**: Всі дії логуються з timestamp, context, reasoning та approval status.

### MCP Hub

- **Registry функціональність**: При заданих `ATLAS_MCP_SERVERS` LLM2 успішно підключається до всіх доступних MCP серверів.
- **Playwright MCP**: Виконує браузерні сценарії (відкриття URL, скріншот) в ізольованому контейнері.
- **TTS MCP**: Агенти можуть "говорити" з вибраними голосами;
  при відмові primary провайдера спрацьовує fallback (включно з coqui_tts).
- **Auto-selection**: MCP Hub автоматично вибирає найефективніший сервер на основі метрик (latency, success rate).

### Dynamic Teams

- **Agent Registry**: Користувач може створювати, налаштовувати та управляти агентами через CRUD API.
- **Team formation**: Система формує команду агентів, пропонує ролі та отримує підтвердження користувача перед запуском.
- **Human-in-the-loop**: Обов'язковий approval gate для критичних дій та команд.

### Infrastructure & Operations

- **Kubernetes deployment**: Всі сервіси успішно розгортаються з персистентними томами.
- **Monitoring**: Prometheus збирає метрики, Grafana відображає дашборди з ключовими KPI.
- **Security**: RBAC, NetworkPolicies та Secrets правильно налаштовані.
- **Backup & Recovery**: Процедури backup/restore для векторної БД та Redis протестовані.

## 10. Чеклісти виконання

### Feature Ready Checklist

- [ ] LLM1 повертає відповідь із "спогадами" (логований source attribution)
- [ ] LLM2 викликає Linear і повертає URL issue
- [ ] LLM3 отримує події Falco і робить принаймні одну безпечну автоматичну дію
- [ ] MCP Hub підключений та функціональний з Playwright, TTS, Automation MCP
- [ ] TTS працює з voice mapping для LLM1/2/3 та fallback на Coqui
- [ ] Agent Registry дозволяє CRUD операції з агентами
- [ ] Dynamic Team Constructor формує команди з human approval

### Ops Ready Checklist

- [ ] Дашборди із ключовими метриками (latency, success rate, resource usage)
- [ ] Алерти на критичні події Falco та системні збої
- [ ] Runbook для ручного override дій LLM3
- [ ] Backup/restore процедури документовані та протестовані
- [ ] Security scan пройдений без критичних вразливостей
- [ ] Load testing показує прийнятну продуктивність

### CI/CD Ready Checklist

- [ ] Unit тести покривають ≥80% критичного коду
- [ ] Integration тести проходять в CI pipeline
- [ ] E2E тести працюють проти staging environment
- [ ] Kubernetes manifests проходять kubeval/kubeconform
- [ ] Docker images будуються та публікуються автоматично
- [ ] Rolling deployment працює без downtime

## 11. Приклади docker-compose доповнень

### MCP TTS Service

```yaml
mcp-tts:
  image: ghcr.io/blacktop/mcp-tts:latest
  ports: ["4004:4004"]
  environment:
    - MCP_PORT=4004
    - ATLAS_TTS_PROVIDERS=say_tts,openai_tts,elevenlabs_tts,google_tts,coqui_tts
    - COQUI_TTS_BASE_URL=http://coqui-tts:5002
    - OPENAI_API_KEY=${OPENAI_API_KEY}
    - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
    - GOOGLE_TTS_API_KEY=${GOOGLE_TTS_API_KEY}
  depends_on:
    - coqui-tts

coqui-tts:
  image: coqui/tts:latest
  ports: ["5002:5002"]
  command: ["--model_name", "tts_models/en/ljspeech/tacotron2-DDC"]
```

### LLM2 з MCP Hub підключенням

```yaml
llm2-orchestrator:
  environment:
    - ATLAS_MCP_SERVERS=playwright,automation,automator,tts,stt
    - ATLAS_MCP_PLAYWRIGHT_URL=http://mcp-playwright:4001
    - ATLAS_MCP_AUTOMATION_URL=http://mcp-automation:4002
    - ATLAS_MCP_AUTOMATOR_URL=http://mcp-automator:4003
    - ATLAS_MCP_TTS_URL=http://mcp-tts:4004
    - ATLAS_LLM2_ALLOW_FALLBACK=false
    - OLLAMA_BASE_URL=http://ollama:11434
```

## 12. Технічні вимоги та архітектурні рішення

### Performance Requirements

- **Response Time**: LLM1 має відповідати протягом 5 секунд для запитів з RAG
- **Throughput**: Система має підтримувати 100+ concurrent користувачів
- **Memory Usage**: Кожен LLM контейнер не більше 8GB RAM
- **Storage**: Vector DB має зростати до 100GB зі збереженням performance

### Reliability Patterns

- **Circuit Breaker**: Для всіх зовнішніх LLM провайдерів (OpenAI, Anthropic)
- **Retry Logic**: Exponential backoff з максимум 3 спробами
- **Health Checks**: Kubernetes liveness/readiness проби для всіх сервісів
- **Graceful Shutdown**: 30-секундний grace period для завершення активних запитів

### Security Requirements

- **Secrets Management**: Kubernetes Secrets для всіх API ключів та credentials
- **Network Isolation**: NetworkPolicies обмежують міжсервісну комунікацію
- **RBAC**: Service Accounts з мінімальними необхідними permissions
- **Audit Logging**: Всі критичні дії LLM3 логуються в structured format

### LLM Provider Configuration

```yaml
# LLM1 Provider Priority
primary: openai       # gpt-4
fallback1: anthropic  # claude-3
fallback2: azure_openai

# LLM2 Local First
primary: ollama       # gpt-oss:latest
fallback: openai      # тільки при ALLOW_FALLBACK=true

# LLM3 Security Focused
primary: openai       # gpt-4 для кращого reasoning
fallback: anthropic   # claude-3
```

### Monitoring & Observability

- **Metrics**: Prometheus збирає custom metrics (LLM latency, token count, success rate)
- **Tracing**: Distributed tracing через OpenTelemetry для multi-agent requests
- **Alerting**: Critical alerts на Falco events, LLM failures, resource exhaustion
- **Dashboards**: Grafana дашборди для operational metrics та business KPIs

## 13. Наступні кроки (я пропоную)

- Перелік ключових вимог та статус у цьому коміті:
  - Об'єднання інструкцій в один документ — Done (оновлено `instruction.md`).
  - Створення `k8s/` манифестів — Deferred (можу згенерувати на наступному кроці).
  - Skeleton агентів (llm1/llm2) — Deferred (пропозиція в "Наступні кроки").

---

Файл оновлено: ця версія `instruction.md` — зведений, деталізований план реалізації ATLAS,
готовий до подальшого перетворення в робочі артефакти (k8s manifests, код агентів, CI workflows).
