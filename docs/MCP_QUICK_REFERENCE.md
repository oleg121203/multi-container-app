# MCP Servers Quick Reference

## Швидкі команди для роботи з MCP серверами

### Управління через скрипт
```bash
# Запуск всіх MCP серверів
./scripts/manage-mcp.sh start

# Зупинка всіх MCP серверів
./scripts/manage-mcp.sh stop

# Перезапуск всіх MCP серверів
./scripts/manage-mcp.sh restart

# Статус контейнерів
./scripts/manage-mcp.sh status

# Перевірка health endpoints
./scripts/manage-mcp.sh health

# Перегляд логів
./scripts/manage-mcp.sh logs

# Пересборка образів
./scripts/manage-mcp.sh build
```

### Прямі Docker Compose команди
```bash
# Запуск окремих сервісів
docker-compose up -d mcp-file-manager
docker-compose up -d mcp-macos-automation  
docker-compose up -d mcp-kubernetes

# Запуск всіх MCP сервісів одразу
docker-compose up -d mcp-file-manager mcp-macos-automation mcp-kubernetes

# Перегляд статусу
docker-compose ps mcp-file-manager mcp-macos-automation mcp-kubernetes

# Зупинка сервісів
docker-compose stop mcp-file-manager mcp-macos-automation mcp-kubernetes

# Пересборка та запуск
docker-compose build mcp-macos-automation
docker-compose up -d mcp-macos-automation
```

### Health Check команди
```bash
# Перевірка всіх серверів
for port in 4006 4007 4009; do
  echo "=== Port $port ==="
  curl -s http://localhost:$port/health | jq .
done

# Окремі перевірки
curl http://localhost:4006/health  # File Manager
curl http://localhost:4007/health  # macOS Automation
curl http://localhost:4009/health  # Kubernetes
```

### Дебагінг команди
```bash
# Логи окремих сервісів
docker-compose logs mcp-file-manager
docker-compose logs mcp-macos-automation
docker-compose logs mcp-kubernetes

# Відстеження логів в реальному часі
docker-compose logs -f mcp-macos-automation

# Підключення до контейнера
docker exec -it multi-container-app-mcp-macos-automation-1 /bin/bash

# Перевірка процесів в контейнері
docker exec multi-container-app-mcp-macos-automation-1 ps aux

# Перевірка X11 в macOS Automation
docker exec multi-container-app-mcp-macos-automation-1 echo $DISPLAY
docker exec multi-container-app-mcp-macos-automation-1 ps aux | grep Xvfb
```

## Порти та сервіси

| Сервіс | Порт | Health URL | Функція |
|--------|------|------------|---------|
| File Manager | 4006 | http://localhost:4006/health | Управління файлами |
| macOS Automation | 4007 | http://localhost:4007/health | GUI автоматизація |
| Kubernetes | 4009 | http://localhost:4009/health | K8s управління |

## Структура файлів

```
agents/mcp_servers/
├── file_manager/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py
├── macos_automation/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── server.py
│   └── start.sh
└── kubernetes/
    ├── Dockerfile
    ├── requirements.txt
    └── server.py
```

## Змінні середовища

```bash
# Порти
MCP_FILE_MANAGER_PORT=4006
MCP_MACOS_PORT=4007  
MCP_K8S_PORT=4009

# GUI налаштування
DISPLAY=:99
AUTOMATION_MODE=safe

# Інтеграція URLs
ATLAS_MCP_FILE_MANAGER_URL=http://mcp-file-manager:4006
ATLAS_MCP_MAC_AUTOMATION_URL=http://mcp-macos-automation:4007
ATLAS_MCP_KUBERNETES_URL=http://mcp-kubernetes:4009
```

## Troubleshooting

### macOS Automation не відповідає
```bash
# Перевірити X11
docker exec container_name echo $DISPLAY
docker exec container_name ps aux | grep Xvfb

# Перезапустити з очищенням
docker-compose stop mcp-macos-automation
docker-compose rm -f mcp-macos-automation
docker-compose up -d mcp-macos-automation
```

### Kubernetes клієнт недоступний
```bash
# Перевірити kubectl
docker exec container_name kubectl version --client

# Перевірити kubeconfig
docker exec container_name ls -la /kubeconfig/
```

### Перевірка портів
```bash
# Які порти зайняті
netstat -tlnp | grep -E '(4006|4007|4009)'

# Перевірка з'єднання
telnet localhost 4006
telnet localhost 4007
telnet localhost 4009
```

## Документація

- [MCP Servers Setup Guide](docs/MCP_SERVERS_SETUP.md)
- [Changelog](CHANGELOG_MCP.md)
- [Docker Compose](compose.yaml)
- [Main README](README.md)
