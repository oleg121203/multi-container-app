# ATLAS — Технічне ТЗ і Архітектурний План для делегування агенту кодування

Мета документа: стисле, однозначне ТЗ для агента кодування з чіткими вимогами, поетапним планом, артефактами, критеріями приймання та чеклістами виконання.

## TL;DR

- Три LLM-агенти з розділеними ролями: LLM1 (інтерфейс + пам'ять через RAG), LLM2 (локальний оркестратор на Ollama + AutoGen/Orkes), LLM3 (наглядач + реакції на аномалії з Falco).
- Дані пам'яті: спеціалізована векторна БД (Qdrant або Milvus) + Redis як семантичний кеш/сесії.
- Інфраструктура: перехід з Docker Compose на Kubernetes (Kompose + допрацювання), StatefulSet для БД, моніторинг Prometheus+Grafana, секрети через Kubernetes Secrets, доступ через RBAC.
- Автоматизація macOS/GUI: безпечний запуск Playwright у ізольованих контейнерах (Apple container) або браузерні робочі простори (Kasm).
- Динамічні команди агентів: реєстр агентів і конструктор команд (AutoGen/MetaGPT) з автопризначенням ролей/персон і затвердженням користувачем.

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
- Оркестрація: AutoGen/MetaGPT як когнітивна оркестрація агентів; MCP Hub — федерація інструментів через Model Context Protocol (контейнеризовані MCP-сервери: Playwright MCP, Automation MCP тощо). Для довготривалих і надійних бізнес-процесів опційно — Orkes (Netflix Conductor).
- Спостережуваність: Prometheus з Grafana.
- Безпека: Falco для подій ядра/контейнерів; Secrets і RBAC у Kubernetes.
- Інтеграції: Linear GraphQL API (issues/tasks), Playwright (automation).

#### MCP Hub — модульні MCP-сервери (контейнери)

- Призначення: «касетний» шар інструментів. Будь-який MCP-сервер додається окремим контейнером і автоматично стає доступним агентам через клієнт MCP.
- Приклади серверів:
  - Playwright MCP (браузерна автоматизація),
  - Automation MCP (загальні задачі автоматизації/інтеграцій),
  - macOS Automator MCP Server (оркестрація нативних дій macOS через Automator/Shortcuts),
  - TTS MCP (голос: blacktop/mcp-tts із кількома провайдерами),
  - Filesystem/Git/HTTP MCP, Browser MCP тощо,
  - STT MCP (розпізнавання мовлення для участі користувача/агентів).
- Дисквері/підключення: LLM2 містить MCP-клієнт, який читає реєстр серверів із env і встановлює з’єднання (HTTP/WebSocket) до кожного з них.
- Кросплатформеність: усі MCP-сервери контейнеризовані (Linux/macOS/Windows). Для headful-браузера — Kasm або Apple container на macOS.
- Конфігурація (env, узгоджений патерн):
  - ATLAS_MCP_SERVERS=playwright,automation,automator,tts,stt,git
  - Для кожного: ATLAS_MCP_{NAME}_ENABLED=true|false, ATLAS_MCP_{NAME}_URL або HOST/PORT,
    ATLAS_MCP_{NAME}_AUTH_* (ключі), ATLAS_MCP_{NAME}_OPTS (додаткові прапори)
- Ескіз docker-compose (довідково):

  ```yaml
  services:
    mcp-playwright:
      image: ghcr.io/example/playwright-mcp:latest
      ports: ["4001:4001"]
      environment:
        - MCP_PORT=4001
        - PLAYWRIGHT_CHROMIUM=true
    mcp-automation:
      image: ghcr.io/example/automation-mcp:latest
      ports: ["4002:4002"]
    mcp-automator:
      image: ghcr.io/example/macos-automator-mcp:latest
      # За потреби: привілеї для доступу до Automator/Shortcuts на macOS-host з ізоляцією
      ports: ["4003:4003"]
    mcp-stt:
      image: ghcr.io/example/stt-mcp:latest
      ports: ["8080:8080"]
  
    llm2-orchestrator:
      # ...існуюча конфігурація LLM2...
      environment:
        - ATLAS_MCP_SERVERS=playwright,automation,automator,tts,stt
        - ATLAS_MCP_PLAYWRIGHT_URL=http://mcp-playwright:4001
        - ATLAS_MCP_AUTOMATION_URL=http://mcp-automation:4002
        - ATLAS_MCP_AUTOMATOR_URL=http://mcp-automator:4003
        - ATLAS_MCP_TTS_URL=http://mcp-tts:4004
        - ATLAS_MCP_STT_URL=http://mcp-stt:8080
  ```

- Безпека: ключі доступу в Kubernetes Secrets; мережеві політики обмежують доступ лише з сервісу LLM2. Логи доступів — у спільний стек спостережуваності.
- Взаємодія з Orkes (опційно): MCP — це «інструменти», Orkes — «процеси» (довгі/надійні). Можуть співіснувати.

##### Політика вибору інструментів і телеметрія

- «Два MCP управління macOS»: Automation MCP і macOS Automator MCP розглядаються як інструменти схожого призначення. Система збирає метрики (успіх/помилки, затримка, кроки/витрати) і автоматично обирає кращий для конкретного типу задачі.
- Маршрутизація: правило за замовчуванням — спробувати інструмент із кращою історичною метрикою успіху для даного intent; фолбек — альтернативний MCP.
- Телеметрія: експортувати лічильники у Prometheus з лейблами mcp_name, action, success, latency_ms; дашборд порівнює ефективність інструментів одного призначення.

##### MCP TTS (обов'язково)

- Сервер: TTS MCP від blacktop (mcp-tts). Дозволяє «хто говорить» серед агентів та вибір провайдера TTS із фолбеком.
- Провайдери: say_tts, elevenlabs_tts, google_tts, openai_tts, а також coqui_tts (через локальний Coqui TTS server).
- Конфігурація (env):
  - ATLAS_TTS_PROVIDERS=say_tts,openai_tts,elevenlabs_tts,google_tts,coqui_tts (порядок = фолбек-ланцюг)
  - Для провайдерів: OPENAI_API_KEY, ELEVENLABS_API_KEY, GOOGLE_TTS_API_KEY тощо
  - Для Coqui: `COQUI_TTS_BASE_URL=http://coqui-tts:5002`
  - Прив'язка голосів до агентів (приклад): ATLAS_TTS_AGENT_VOICE_LLM1=voiceA, ATLAS_TTS_AGENT_VOICE_LLM2=voiceB, ATLAS_TTS_AGENT_VOICE_LLM3=voiceC
- Ескіз docker-compose доповнення:

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
      image: ghcr.io/coqui-ai/tts-cpu:latest
      ports: ["5002:5002"]
      command: ["python3", "TTS/server/server.py", "--model_name", "tts_models/en/vctk/vits"]
  ```

- Зауваження: якщо офіційний образ mcp-tts відсутній або потрібно додати coqui_tts як новий провайдер — дозволено створити тонкий «шлюз» усередині mcp-tts, що перенаправляє запити до COQUI_TTS_BASE_URL.

Безпека/приватність аудіо: TTS може відправляти текст/аудіо провайдерам поза кластером. Використовуйте окремі ключі, обмежуйте мережеві правила (NetworkPolicy), вмикайте анонімізацію тексту за потреби та зберігання аудіо — тільки у внутрішніх сховищах.

Мінімальний контракт TTS MCP (узагальнено):

- POST /speak { text, voice, agent, provider? } → { url | bytes }
- GET /voices → { voices: string[] }
- GET /health → { status: "ok" }
- Метрики: Prometheus counters/gauges з лейблами provider, agent, voice, success; гістрограма latency_ms.

##### Live Debate Mode (жива командна дискусія з TTS/STT)

- Призначення: режим живої дискусії між агентами з можливістю долучення користувача голосом. У кінці — обов'язковий конструктивний підсумок і план дій (ідеологія: «в спорі народжується істина»).
- Модерація: автоматичний модератор (LLM2) або людина; контролює регламент, черговість, таймбокс і етику.
- Канали: TTS озвучує репліки агентів; STT перетворює мовлення користувача/агентів у текст; основний чат — текстовий лог для аудиту.

Налаштування (env):

- ATLAS_DEBATE_MODE_ENABLED=true|false
- ATLAS_DEBATE_INTENSITY=0..1 (енергійність аргументації)
- ATLAS_DEBATE_AGGRESSION=0..1 (ступінь наполегливості/контраргументації; без токсичності)
- ATLAS_DEBATE_INTERRUPT_POLICY=strict|moderate|free
- ATLAS_DEBATE_TURN_SECONDS=30
- ATLAS_DEBATE_MAX_ROUNDS=5
- ATLAS_DEBATE_MODERATOR=auto|user|agent:{NAME}
- ATLAS_DEBATE_SUMMARY_STYLE=structured|narrative|bullets
- ATLAS_DEBATE_DEVILS_ADVOCATE_RATE=0..1
- ATLAS_DEBATE_STEELMAN=true|false
- ATLAS_DEBATE_CONSENSUS_REQUIRED=hard|soft

STT/TTS параметри (приклад): ATLAS_STT_PROVIDER=whisper|google|deepgram|vosk, ATLAS_STT_LANGUAGE=uk-UA; ATLAS_TTS_LANG=uk; GOOGLE_TTS_LANGUAGE=uk-UA.

Безпека/етика: заборонені образи/мова ненависті; модератор припиняє некоректні дії; усі рішення — в логах.


##### Платформа «Реєстр агентів і Конструктор команд» (AutoGen/MetaGPT)

- Призначення: динамічно формувати «робочі групи» під довготривалі задачі. Користувач задає лише імена агентів (5–20), обирає провайдера/модель і вводить API‑ключі; система автоматично призначає ролі, поведінку/персону, дозволені інструменти.
- Базова статична команда: попередньо визначена команда на випадок швидких задач або коли динаміка не потрібна.
- Динамічні команди: для кожної задачі — оцінка домену/складності/тривалості → вибір ролей і підбір агентів із реєстру.
- Оркестрація: AutoGen/MetaGPT координує міжагентну взаємодію; для довгих процесів — Orkes (workflow), інструменти — через MCP Hub.

Ролі (приклади шаблонів):

- Lead/Coordinator, Planner, Researcher, Coder, Reviewer, Ops/SRE, SecOps, QA, PM/Scribe.

Зберігання і конфіг:

- Реєстр агентів: JSON/YAML або БД. Шлях за змовчанням: `ATLAS_AGENT_REGISTRY_PATH`.
- Шаблони ролей/персон: YAML у `ATLAS_ROLE_TEMPLATES_PATH`.
- Секрети (API‑ключі) — тільки через Secrets (K8s/ENV), шифрування в покої рекомендовано.

Мінімальні схеми (приклад):

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

API (узагальнено):

- POST /agents { name, provider, model, apiKeyRef|apiKey, skills?, tools? } → { id }
- POST /teams { name, members[], strategy: "static"|"dynamic", roleTemplates? } → { id }
- POST /team/build { taskId, strategy?, constraints? } → { teamId, members: [{name, role}] }
- POST /team/approve { teamId, changes? } → { status }

Поведенчі політики:

- Автопризначення ролей за шаблонами + підсилення «персони» через системні промпти.
- Gate «людина-в-петлі»: перед запуском — підтвердження команди користувачем або правки.
- Guardrails: ліміти вартості/запитів, rate limiting, аудит.


##### Базовий пакет MCP (рекомендація)

- Ціль: «укріпити» систему стартовим набором інструментів, який покриває часті потреби.
- Склад (може бути адаптований агентом на власний розсуд):
  - Playwright MCP (браузерні сценарії),
  - Automation MCP (загальна автоматизація/інтеграції),
  - macOS Automator MCP (нативні дії на macOS),
  - TTS MCP (mcp-tts) із провайдерами та coqui_tts як локальним фолбеком,
  - Redis MCP або адаптер до Redis (якщо потрібні черги/кеш),
  - Buffer/Memory MCP (простий in‑memory буфер як тимчасове сховище проміжних артефактів),
  - Filesystem/Git/HTTP MCP (робота з файлами, VCS, HTTP).
    - STT MCP (розпізнавання мовлення для участі користувача/агентів),
- Примітка: якщо готового MCP‑сервера для Redis/Buffer немає, агент додає тонкий адаптер (обгортку) або еквівалентний інструмент.

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

## Політика фронтенду

- Основний веб‑інтерфейс буде розроблятися після завершення бекенду та стабілізації API/контрактів.
- Допускається створення попередніх веб‑інтерфейсів для демонстрації або тестування, але лише «реальних» — без симуляцій/макетів/демо‑режимів. Всі інтеракції мають бути повністю підключені до бекенду та інструментів (MCP/Orkes) і працювати на тих же контрактах.
- Пріоритет — CLI/HTTP API та інтеграційні тести; фронтенд з’являється як тонкий шар поверх усталених контрактів.

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

### Фаза 4 — Teams & TTS (DoD)

- Реєстр агентів і базова статична команда працюють (CRUD + конфіги ролей/персон).
- Динамічне складання команди під задачу через AutoGen/MetaGPT з підтвердженням користувача.
- Мапінг голосів TTS до LLM1/2/3, працює фолбек провайдерів; метрики експортуються в Prometheus.

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
- MCP-01: Зібрати MCP Hub: додати контейнерні MCP-сервери (Playwright MCP, Automation MCP), реєстр через ATLAS_MCP_SERVERS, підключення з LLM2.
- MCP-02: Додати macOS Automator MCP Server і об'єднати з Automation MCP як «два MCP управління macOS».
- MCP-03: Реалізувати політику авто-вибору MCP за метриками (success rate/latency) з Prometheus-експортерами.
- MCP-04: Базовий пакет MCP: Playwright, Automation, Automator, Redis/Buffer, FS/Git/HTTP; .env.example з ATLAS_MCP_*.
- MCP-05: Інтегрувати TTS MCP (mcp-tts) з провайдерами say/elevenlabs/google/openai та coqui_tts через локальний Coqui server.
- MCP-06: Зв'язати голоси з агентами (LLM1/2/3) через env та забезпечити фолбек провайдера.
- TEAM-01: Реєстр агентів (CRUD + зберігання): моделі, API, інтеграція з Secrets.
- TEAM-02: Рольові шаблони/персони (YAML) і автопризначення ролей.
- TEAM-03: Побудова динамічної команди (AutoGen/MetaGPT) за task intent + gate на підтвердження.
- TEAM-04: Інтеграція з Orkes для довгих задач (workflow) + MCP Hub для інструментів.
- TEAM-05: Дашборд ефективності команд: тривалість, успішність, вартість по ролях/провайдерах.
- UI-01: Після стабілізації бекенд‑контрактів додати мінімальний «реальний» веб‑інтерфейс (без моків/демо) поверх існуючих API.
- UI-02: Додати інтеграційні e2e тести фронтенду проти живого бекенду (Playwright) і включити в CI.

## Критерії приймання (Acceptance)

- Запит користувача → LLM1 → створено issue у Linear з коректними полями.
- Пам'ять: повторний запит через ≥24 години використовує релевантний контекст із векторної БД.
- Falco-івент високого пріоритету → рішення LLM3 → застосовано обрану дію (dry-run/реально) і зафіксовано в логах.
- Дашборд Grafana показує метрики: RT LLM1/2, обсяг пам'яті, к-ть подій Falco, успіхи оркестрації.
- LLM1/LLM3: перемикання провайдера/моделі через env без змін коду; підтверджено роботою фолбек-ланцюга при симуляції відмови primary.
- LLM2: за замовчуванням використовує локальну Ollama gpt-oss:latest; при примусовій симуляції відмови й дозволі фолбеку запускається наступний у ланцюжку та це логується.
- MCP Hub: при заданих ATLAS_MCP_SERVERS LLM2 успішно підключається щонайменше до Playwright MCP і виконує один сценарій (наприклад, відкриття URL і зняття скріншоту), подія фіксується у логах.
- «Два MCP управління macOS»: і Automation MCP, і macOS Automator MCP доступні; система виконує один і той самий намір через обидва, збирає метрики і обирає кращий інструмент при повторі.
- Дашборд «Ефективність MCP»: є панель у Grafana з порівнянням success/latency по mcp_name для інструментів однакового призначення.
- TTS MCP: LLM‑агенти можуть «говорити» з вибраними голосами; при відмові primary‑провайдера TTS спрацьовує фолбек (зокрема coqui_tts через локальний сервер) і подія логуються.
- Команди: користувач вказує лише імена + провайдер/модель/ключі; система формує команду, пропонує ролі, отримує підтвердження і запускає виконання.
- Динаміка: для нової задачі будується команда за intent; для простої — доступна базова статична команда.
- Фронтенд‑політика: основний веб‑інтерфейс з’являється після бекенду; якщо зібраний ранній UI — усі його дії виконуються реально через бекенд/API без симуляцій і проходять e2e тести.

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
- Код: модулі агентів (LLM1/2/3) із конфігами; адаптери до Linear/Falco/Orkes/Playwright  і так далі...
- Документація: README з запуском, дашборди Grafana.json, приклади подій Falco, схеми колекцій RAG.

## Примітка

Цей документ є переформатованою, стислою версією вихідного опису ATLAS з акцентом на делегування роботі агента кодування. Оригінальні ідеї збережено, структура — оптимізована під виконання.
