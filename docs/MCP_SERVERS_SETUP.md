# MCP Servers Configuration Guide

Цей документ описує налаштування всіх MCP (Model Context Protocol) серверів в multi-container-app проекті.

## Огляд MCP серверів

Система включає 3 основних MCP сервери:

1. **File Manager MCP** (порт 4006) - управління файлами
2. **macOS Automation MCP** (порт 4007) - GUI автоматизація  
3. **Kubernetes MCP** (порт 4009) - управління K8s ресурсами

## 1. File Manager MCP Server

### Файли конфігурації:
- `agents/mcp_servers/file_manager/Dockerfile`
- `agents/mcp_servers/file_manager/requirements.txt`
- `agents/mcp_servers/file_manager/server.py`

### Основні функції:
- Читання та запис файлів
- Створення директорій
- Перегляд структури файлової системи
- Безпечне управління файлами з валідацією шляхів

### Health endpoint:
```bash
curl http://localhost:4006/health
```

### Залежності:
```txt
mcp>=1.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
aiofiles>=23.2.0
pathvalidate>=3.2.0
python-multipart>=0.0.6
```

## 2. macOS Automation MCP Server

### Файли конфігурації:
- `agents/mcp_servers/macos_automation/Dockerfile`
- `agents/mcp_servers/macos_automation/requirements.txt`
- `agents/mcp_servers/macos_automation/server.py`
- `agents/mcp_servers/macos_automation/start.sh`

### Особливості налаштування:

#### Dockerfile включає:
- X11 сервер (Xvfb) для headless GUI
- Системні залежності: `xvfb`, `x11-utils`, `x11-xserver-utils`
- Python tkinter: `python3-tk`, `python3-dev`

#### start.sh script:
- Очищення X11 locks
- Запуск Xvfb на дисплеї :99
- Перевірка з'єднання з X11
- Налаштування змінної DISPLAY=:99

### Основні функції:
- Скріншоти екрану
- Клік миші та керування курсором
- Натискання клавіш
- Розпізнавання образів на екрані
- Безпечна автоматизація з FAILSAFE

### Health endpoint:
```bash
curl http://localhost:4007/health
```

Відповідь включає статус PyAutoGUI:
```json
{
  "status": "healthy",
  "service": "macos-automation-mcp",
  "automation_mode": "safe",
  "pyautogui_available": false
}
```

### Залежності:
```txt
mcp>=1.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
pyautogui>=0.9.54
pillow>=10.0.0
opencv-python>=4.8.0
```

### Змінні середовища:
- `DISPLAY=:99` - X11 display для headless режиму
- `AUTOMATION_MODE=safe` - режим безпеки
- `MCP_MACOS_PORT=4007` - порт сервера

## 3. Kubernetes MCP Server

### Файли конфігурації:
- `agents/mcp_servers/kubernetes/Dockerfile`
- `agents/mcp_servers/kubernetes/requirements.txt`
- `agents/mcp_servers/kubernetes/server.py`

### Особливості налаштування:

#### Dockerfile включає:
- kubectl CLI tool
- CA certificates для HTTPS з'єднань
- Python kubernetes client

### Основні функції:
- Список pods, services, deployments
- Створення та видалення K8s ресурсів
- Перегляд логів pods
- Управління namespace
- Застосування YAML конфігурацій

### Health endpoint:
```bash
curl http://localhost:4009/health
```

Відповідь включає статус K8s клієнта:
```json
{
  "status": "healthy",
  "service": "kubernetes-mcp",
  "k8s_client_available": true,
  "k8s_configured": false,
  "kubeconfig_path": "/kubeconfig/config",
  "default_namespace": "default"
}
```

### Залежності:
```txt
mcp>=1.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
kubernetes>=28.1.0
pyyaml>=6.0
aiofiles>=23.2.0
```

### Змінні середовища:
- `MCP_K8S_PORT=4009` - порт сервера
- `KUBECONFIG=/kubeconfig/config` - шлях до kubeconfig

## Docker Compose конфігурація

### Ports mapping:
```yaml
mcp-file-manager:
  ports:
    - "4006:4006"

mcp-macos-automation:
  ports:
    - "4007:4007"

mcp-kubernetes:
  ports:
    - "4009:4009"
```

### Health checks:
Всі сервери мають health check endpoints:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:XXXX/health"]
  interval: 30s
  timeout: 10s
  start-period: 5s
  retries: 3
```

## Запуск та тестування

### Запуск всіх MCP серверів:
```bash
docker-compose up -d mcp-file-manager mcp-macos-automation mcp-kubernetes
```

### Перевірка статусу:
```bash
# File Manager
curl http://localhost:4006/health

# macOS Automation  
curl http://localhost:4007/health

# Kubernetes
curl http://localhost:4009/health
```

### Перевірка логів:
```bash
docker-compose logs mcp-file-manager
docker-compose logs mcp-macos-automation
docker-compose logs mcp-kubernetes
```

## Troubleshooting

### macOS Automation MCP:
- Перевірте чи запущений Xvfb: `docker exec container_name ps aux | grep Xvfb`
- Перевірте X11 display: `docker exec container_name echo $DISPLAY`
- Логи PyAutoGUI: шукайте warnings про tkinter або libgthread

### Kubernetes MCP:
- Перевірте kubectl: `docker exec container_name kubectl version --client`
- Перевірте kubeconfig: `docker exec container_name ls -la /kubeconfig/`

### File Manager MCP:
- Перевірте права доступу до файлів
- Перевірте volume mounts в docker-compose.yml

## Архітектурні рішення

### Чому Xvfb замість X2Go для GUI автоматизації:
- **X2Go** - призначена для інтерактивних користувачів і remote desktop доступу
- **Xvfb** - спеціально для headless GUI автоматизації в контейнерах
- Мінімальні ресурси та простота налаштування
- Ідеальна інтеграція з PyAutoGUI

### Безпека:
- PyAutoGUI FAILSAFE увімкнено
- Валідація шляхів у File Manager
- Режим "safe" для automation сервера
- Health checks для моніторингу

## Інтеграція з ATLAS системою

MCP сервери інтегровані з основною ATLAS системою через змінні середовища:
```yaml
environment:
  - ATLAS_MCP_FILE_MANAGER_URL=http://mcp-file-manager:4006
  - ATLAS_MCP_MAC_AUTOMATION_URL=http://mcp-macos-automation:4007
  - ATLAS_MCP_KUBERNETES_URL=http://mcp-kubernetes:4009
```

Це дозволяє ATLAS агентам використовувати MCP сервери для розширених можливостей автоматизації та управління інфраструктурою.
