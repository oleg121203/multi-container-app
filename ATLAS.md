# ATLAS — Технічне ТЗ і Архітектурний План для делегування агенту кодування

Мета документа: стисле, однозначне ТЗ для агента кодування з чіткими вимогами, поетапним планом, артефактами, критеріями приймання та чеклістами виконання.

## TL;DR

- Три LLM-агенти з розділеними ролями: LLM1 (інтерфейс + пам'ять через RAG), LLM2 (локальний оркестратор на Ollama + AutoGen/Orkes), LLM3 (наглядач + реакції на аномалії з Falco).
- Дані пам'яті: спеціалізована векторна БД (Qdrant або Milvus) + Redis як семантичний кеш/сесії.
- Інфраструктура: перехід з Docker Compose на Kubernetes (Kompose + допрацювання), StatefulSet для БД, моніторинг Prometheus+Grafana, секрети через Kubernetes Secrets, доступ через RBAC.
- Автоматизація macOS/GUI: безпечний запуск Playwright у ізольованих контейнерах (Apple container) або браузерні робочі простори (Kasm).

## Обсяг і цілі

### Цілі

- Реалізувати основу багатоагентної системи ATLAS з чіткою оркестрацією робочих процесів.
- Забезпечити стійку пам'ять користувача (RAG) і прозору спостережуваність/безпеку.
- Підготувати міграцію з docker-compose до Kubernetes з мінімальною ручною доробкою.

### Поза обсягом (на зараз)

- Повна бізнес-логіка домену замовника, UI/UX фронтенда та продакшн SLO/SLA.
- Глибока інтеграція з усіма зовнішніми сервісами, крім необхідних (Linear, Orkes, Falco).

## Огляд системи

### Ролі агентів

| Агент | Призначення | Основні обов'язки | Технології/інструменти |
|---|---|---|---|
| LLM1 | Користувацький інтерфейс | Розмова, збереження контексту, формалізація завдань | RAG, Redis, Qdrant/Milvus |
| LLM2 | Оркестратор/Планувальник | Декомпозиція, призначення інструментів, виконання | Ollama (локально), AutoGen/MetaGPT, Orkes (Netflix Conductor), Playwright, Linear API |
| LLM3 | Наглядач/Безпека | Аналіз аномалій, пояснення, автоматизоване реагування | Falco, Kubernetes API, Prometheus/Grafana |

### Архітектурні компоненти (високий рівень)

- RAG-шар пам'яті: векторна БД (Qdrant або Milvus) + Redis.
- Оркестрація: AutoGen/MetaGPT як когнітивна оркестрація агентів; MSP Hub як платформа виконання (напр., Orkes на базі Netflix Conductor) для довгих і стійких робочих процесів.
- Спостережуваність: Prometheus з Grafana.
- Безпека: Falco для подій ядра/контейнерів; Secrets і RBAC у Kubernetes.
- Інтеграції: Linear GraphQL API (issues/tasks), Playwright (automation).

## Функціональні вимоги (контракти)

### LLM1 — пам'ять і RAG

- Короткочасна пам'ять: буфер сесії для останніх реплік.
- Довготривала пам'ять: індексування важливих сегментів у векторній БД.
- Пошук: запит → ембединг → kNN пошук → топ-k «спогадів» додаються до промпту.

Дані (мінімальна схема колекції):

- id: string (ULID/UUID)
- text: string (нормалізований фрагмент діалогу)
- embedding: float[]
- metadata: { userId, ts, tags[] }

#### Провайдери та моделі для LLM1 (дефолт + фолбек)

- Підтримувані провайдери: OpenAI, Mistral, Google Gemini, Ollama (локально).
- Дефолт (рекомендовано):
  - OpenAI: gpt-4o-mini (баланс якості/затримки) або аналог класу 4.x mini.
  - Альтернатива з низькою затримкою: Gemini 1.5 Flash / Mistral Small latest.
  - Локально: Ollama llama3.1:8b-instruct або qwen2.5:7b-instruct.
- Фолбек-ланцюг (приклад, редагується конфігом):
  - openai:gpt-4o-mini → mistral:mistral-small-latest → gemini:gemini-1.5-flash → ollama:llama3.1:8b-instruct.
- Налаштування (env):
  - ATLAS_LLM1_PROVIDER, ATLAS_LLM1_MODEL, ATLAS_LLM1_API_BASE, ATLAS_LLM1_API_KEY
  - ATLAS_LLM1_FALLBACKS (кома-сепаратед список у форматі provider:model)
  - ATLAS_LLM_TIMEOUT_MS, ATLAS_LLM_RETRY_COUNT
- Політика фолбеку: активується при таймауті/5xx/429; логуються всі спроби з вибраним провайдером/моделлю.

### LLM2 — оркестрація і інструменти

- Підтримка локальної моделі через Ollama для приватності/затримок.
- Фреймворк агентів (AutoGen/MetaGPT) з інструментами:
  - Linear: створення/оновлення issue, зміна статусу/пріоритету.
  - Playwright: сценарії браузерної автоматизації (безпечно виконуються).
  - Orkes: запуск/моніторинг довгих робочих процесів.

Інтерфейс Linear (GraphQL, контракт високого рівня):

- mutation CreateIssue(input: { title, description, priority, labelIds }): returns { id, url }
- mutation UpdateIssue(id, input: { stateId, assigneeId, priority }): returns { id, state { name } }

#### Провайдер і модель для LLM2 (строго)

- Primary (обов'язково): локальна Ollama з моделлю gpt-oss:latest.
- Віддалені провайдери в primary заборонені.
- Фолбек (за потреби й лише за умов): OpenAI/Mistral/Gemini/Ollama (інші локальні моделі), дефолтний ланцюжок:
  - ollama:gpt-oss:latest → openai:gpt-4o-mini → mistral:mistral-large-latest → gemini:gemini-1.5-pro.
- Умови активації фолбеку: healthcheck локальної моделі провалюється N разів поспіль АБО явно встановлено ATLAS_LLM2_ALLOW_FALLBACK=true.
- Налаштування (env): ATLAS_LLM2_PROVIDER=ollama, ATLAS_LLM2_MODEL=gpt-oss:latest, ATLAS_LLM2_FALLBACKS, ATLAS_LLM2_ALLOW_FALLBACK, ATLAS_LLM_TIMEOUT_MS.
- Аудит: кожен відхід від локальної Ollama фіксується в журналах із причиною.

### LLM3 — нагляд і реакції

- Вхід: події Falco у форматі JSON.
- Обов'язки: класифікація/пояснення/пріоритезація події; рішення про дію.
- Дії (через K8s API): cordon/drain ноди, видалення/ізоляція pod, застосування NetworkPolicy.

Приклад полів події (узагальнено):

- output, rule, priority, time, hostname
- output_fields: { evt.type, proc.name, user.name, k8s.ns.name, k8s.pod.name, fd.sip, fd.sport }

#### Провайдери та моделі для LLM3 (дефолт + фолбек)

- Підтримувані провайдери: OpenAI, Mistral, Google Gemini, Ollama (локально).
- Дефолт (рекомендовано для аналітики/пояснень із помірною вартістю):
  - OpenAI: gpt-4o-mini або аналог 4.x mini.
  - Mistral: mistral-small-latest (latency/cost), за потреби large.
  - Gemini: 1.5-pro для детальних пояснень або 1.5-flash для швидких відповідей.
  - Ollama: llama3.1:8b-instruct / qwen2.5:7b-instruct локально.
- Фолбек-ланцюг (приклад): openai:gpt-4o-mini → gemini:gemini-1.5-flash → mistral:mistral-small-latest → ollama:llama3.1:8b-instruct.
- Налаштування (env): ATLAS_LLM3_PROVIDER, ATLAS_LLM3_MODEL, ATLAS_LLM3_API_BASE, ATLAS_LLM3_API_KEY, ATLAS_LLM3_FALLBACKS, ATLAS_LLM_TIMEOUT_MS.

## Нефункціональні вимоги

- Приватність: використання локальної моделі (Ollama) для LLM2.
- Масштабованість: StatefulSet для БД, динамічні PVC, topology spread/anti-affinity.
- Спостережуваність: ключові метрики для агентів/оркестрації/черг; базові дашборди Grafana.
- Безпека: Secrets для ключів, RBAC принцип найменших привілеїв, аудит дій LLM3.

## Деплой і середовище

### З docker-compose до Kubernetes

- Використати Kompose для конвертації, для stateful служб — контролер statefulset.
- Доробити readiness/liveness probes, ресурси, storageClass, мережеві політики.

### Бази даних і зберігання

- Qdrant (простота/низька затримка) на старті; міграційний шлях на Milvus для high-throughput.
- Окремі PVC на pod; резервне копіювання на рівні томів.

### Автоматизація GUI на macOS

- Безпечний запуск Playwright у контейнері з ізоляцією рівня VM (Apple container) або Kasm workspaces.

## План впровадження (фази MVP)

### Фаза 1 — Infrastructure MVP (DoD)

- Кластер K8s (локально/хмара), встановлені Prometheus+Grafana, базовий логінг.
- Згенеровані маніфести з Kompose, ручне допрацювання для stateful сервісів.

### Фаза 2 — Agent MVP (DoD)

- LLM1 з RAG (Qdrant/Redis), інтеграція пам'яті; LLM2 на Ollama + AutoGen з інструментом Linear.
- Демонстраційний флоу: «користувач просить задачу → issue у Linear → відслідковується статус».

### Фаза 3 — Automation & Security (DoD)

- LLM3 підключений до потоку Falco, класифікація подій, мінімум 2 автоматизовані реакції.
- Безпечне виконання Playwright-сценарію в ізольованому контейнері.

## Беклог задач для агента кодування

- INF-01: Додати docker-compose сервіси для Qdrant/Milvus і Redis з персистентністю.
- INF-02: Провести kompose convert, додати probes/resources/PVC/affinity вручну.
- OBS-01: Розгорнути Prometheus+Grafana; створити базовий дашборд агентів.
- MEM-01: Реалізувати шар RAG (індексація/пошук) із контрактом колекції.
- ORC-01: Підняти Ollama, інтегрувати AutoGen/MetaGPT; додати tool «Linear» (GraphQL).
- ORC-02: Підключити Orkes для довгих процесів; мінімальний workflow-шаблон.
- SEC-01: Інсталювати Falco; прокинути події у LLM3; додати дії cordon/drain/pod delete.
- GUI-01: Налаштувати безпечний запуск Playwright у Apple container або Kasm.
- OPS-01: Secrets/RBAC: виділені ролі для інструментів; огляд аудит-логів.
- CFG-01: Абстракція провайдерів LLM (OpenAI/Mistral/Gemini/Ollama) з єдиним інтерфейсом і фолбек-ланцюгом (LLM1/LLM3).
- CFG-02: Жорстка прив'язка LLM2 до локальної Ollama gpt-oss:latest + healthcheck і контрольований фолбек.

## Критерії приймання (Acceptance)

- Запит користувача → LLM1 → створено issue у Linear з коректними полями.
- Пам'ять: повторний запит через ≥24 години використовує релевантний контекст із векторної БД.
- Falco-івент високого пріоритету → рішення LLM3 → застосовано обрану дію (dry-run/реально) і зафіксовано в логах.
- Дашборд Grafana показує метрики: RT LLM1/2, обсяг пам'яті, к-ть подій Falco, успіхи оркестрації.
- LLM1/LLM3: перемикання провайдера/моделі через env без змін коду; підтверджено роботою фолбек-ланцюга при симуляції відмови primary.
- LLM2: за замовчуванням використовує локальну Ollama gpt-oss:latest; при примусовій симуляції відмови й дозволі фолбеку запускається наступний у ланцюжку та це логується.

## Ризики і пом'якшення

- Складність конвертації Kompose: мінімізувати через labels у compose; мати чек-лист ручних правок.
- Ізоляція браузера: використовувати контейнер з VM-ізоляцією (Apple container) замість «привілейованих» запусків.
- Локальна LLM продуктивність: кешування через Redis; чіткі межі контексту; offloading довгих задач в Orkes.

## Чеклісти виконання

### Dev ready

- [ ] Окремі простори імен K8s: core, data, observability, security.
- [ ] StorageClass і PVC для Qdrant/Milvus, Redis; резервні копії.
- [ ] Secrets для Linear/Orkes/інші ключі; RBAC налаштовано.

### Feature ready

- [ ] LLM1 повертає відповідь із «спогадами» (логований source attribution).
- [ ] LLM2 викликає Linear і повертає URL issue.
- [ ] LLM3 отримує події Falco і робить принаймні одну безпечну автоматичну дію.

### Ops ready

- [ ] Дашборди із ключовими метриками.
- [ ] Алерти на критичні події Falco.
- [ ] Runbook для ручного override дій LLM3.

## Додаток A. Мінімальні артефакти, що очікуються

- Інфра: папка k8s/ з маніфестами (deploy/statefulset/service/ingress/pvc), values/ для параметрів.
- Код: модулі агентів (LLM1/2/3) із конфігами; адаптери до Linear/Falco/Orkes/Playwright.
- Документація: README з запуском, дашборди Grafana.json, приклади подій Falco, схеми колекцій RAG.

## Примітка

Цей документ є переформатованою, стислою версією вихідного опису ATLAS з акцентом на делегування роботі агента кодування. Оригінальні ідеї збережено, структура — оптимізована під виконання.
