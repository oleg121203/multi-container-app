# Multi-Container ATLAS Application

Проект багатоконтейнерної AI системи ATLAS з інтегрованими MCP (Model Context Protocol) серверами для автоматизації та управління інфраструктурою.

## Архітектура системи

### Основні компоненти

1. **ATLAS Core** - основна AI система з агентами
2. **MCP Servers** - спеціалізовані сервери для розширення функціональності:
   - File Manager MCP (порт 4006) - управління файлами
   - macOS Automation MCP (порт 4007) - GUI автоматизація
   - Kubernetes MCP (порт 4009) - управління K8s ресурсами
3. **Web Interface** - веб-інтерфейс для взаємодії
4. **Monitoring** - система моніторингу та логування

### MCP Servers

Система включає 3 спеціалізованих MCP сервера:

- **File Manager**: Безпечне управління файлами з валідацією шляхів
- **macOS Automation**: GUI автоматизація через PyAutoGUI з Xvfb для headless режиму
- **Kubernetes**: Управління K8s ресурсами через kubectl та Python client

## Швидкий старт

### Запуск всієї системи

```bash
# Клонування репозиторію
git clone <repository-url>
cd multi-container-app

# Запуск всіх сервісів
docker-compose up -d

# Перевірка статусу MCP серверів
curl http://localhost:4006/health  # File Manager
curl http://localhost:4007/health  # macOS Automation
curl http://localhost:4009/health  # Kubernetes
```

### Запуск тільки MCP серверів

```bash
# Запуск MCP серверів
docker-compose up -d mcp-file-manager mcp-macos-automation mcp-kubernetes

# Перевірка статусу
echo "=== MCP Servers Status ==="
curl -s http://localhost:4006/health | jq .
curl -s http://localhost:4007/health | jq .
curl -s http://localhost:4009/health | jq .
```

## Структура проекту

```
multi-container-app/
├── agents/
│   ├── mcp_servers/
│   │   ├── file_manager/          # MCP сервер для управління файлами
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   └── server.py
│   │   ├── macos_automation/      # MCP сервер для GUI автоматизації
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   ├── server.py
│   │   │   └── start.sh          # Скрипт запуску з Xvfb
│   │   └── kubernetes/            # MCP сервер для K8s управління
│   │       ├── Dockerfile
│   │       ├── requirements.txt
│   │       └── server.py
│   └── <інші агенти>
├── compose.yaml                   # Docker Compose конфігурація
├── docs/
│   └── MCP_SERVERS_SETUP.md      # Детальна документація MCP серверів
└── README.md
```

## Особливості налаштування

### macOS Automation MCP

Цей сервер використовує Xvfb (X Virtual Framebuffer) для headless GUI автоматизації:

- **X11 Display**: `:99` для віртуального екрану
- **PyAutoGUI**: Безпечна автоматизація з FAILSAFE
- **Залежності**: tkinter, X11 утиліти, Xvfb

### Kubernetes MCP

Включає повну інтеграцію з Kubernetes:

- **kubectl CLI**: Встановлений в контейнері
- **Python client**: Для програмного управління
- **kubeconfig**: Підтримка зовнішніх конфігурацій

### File Manager MCP

Безпечне управління файлами:

- **Валідація шляхів**: Захист від path traversal атак
- **Async операції**: Ефективна робота з файлами
- **Multipart uploads**: Підтримка завантаження файлів

## Моніторинг та дебагінг

### Health checks

Всі MCP сервери мають health endpoints:

```bash
# Перевірка всіх серверів одночасно
for port in 4006 4007 4009; do
  echo "=== Port $port ==="
  curl -s http://localhost:$port/health | jq .
  echo
done
```

### Логи

```bash
# Перегляд логів окремих сервісів
docker-compose logs mcp-file-manager
docker-compose logs mcp-macos-automation
docker-compose logs mcp-kubernetes

# Відстеження логів в реальному часі
docker-compose logs -f mcp-macos-automation
```

### Troubleshooting

#### macOS Automation:
- Перевірте X11: `docker exec container_name echo $DISPLAY`
- Перевірте Xvfb: `docker exec container_name ps aux | grep Xvfb`

#### Kubernetes:
- Перевірте kubectl: `docker exec container_name kubectl version --client`

## Змінні середовища

```bash
# MCP Ports
MCP_FILE_MANAGER_PORT=4006
MCP_MACOS_PORT=4007
MCP_K8S_PORT=4009

# Automation settings
AUTOMATION_MODE=safe
CLICK_DELAY=0.1
MOVE_DURATION=0.5

# Display for headless GUI
DISPLAY=:99
```

## Документація

- [MCP Servers Setup Guide](docs/MCP_SERVERS_SETUP.md) - детальне налаштування
- [Docker Compose Reference](compose.yaml) - конфігурація контейнерів

## Підтримка

Система протестована на:
- Docker Desktop для macOS
- Linux containers
- ARM64 та AMD64 архітектури

Для питань та проблем створюйте issue в репозиторії.
