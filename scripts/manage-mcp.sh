#!/bin/bash

# MCP Servers Management Script
# Скрипт для управління та перевірки MCP серверів

set -e

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# MCP сервери та порти (для старих версій bash)
MCP_SERVERS="mcp-file-manager:4006 mcp-macos-automation:4007 mcp-kubernetes:4009"

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}   MCP Servers Management Script${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

print_usage() {
    echo "Використання: $0 {start|stop|restart|status|health|logs|build}"
    echo
    echo "Команди:"
    echo "  start   - Запуск всіх MCP серверів"
    echo "  stop    - Зупинка всіх MCP серверів"
    echo "  restart - Перезапуск всіх MCP серверів"
    echo "  status  - Статус контейнерів"
    echo "  health  - Перевірка health endpoints"
    echo "  logs    - Перегляд логів"
    echo "  build   - Пересборка образів"
    echo
}

start_servers() {
    echo -e "${YELLOW}Запускаю MCP сервери...${NC}"
    echo
    
    for server_port in $MCP_SERVERS; do
        local server=$(echo "$server_port" | cut -d: -f1)
        echo -e "Starting ${BLUE}$server${NC}..."
        docker-compose up -d "$server"
    done
    
    echo
    echo -e "${GREEN}Очікування готовності серверів...${NC}"
    sleep 5
    
    check_health
}

stop_servers() {
    echo -e "${YELLOW}Зупиняю MCP сервери...${NC}"
    echo
    
    for server_port in $MCP_SERVERS; do
        local server=$(echo "$server_port" | cut -d: -f1)
        echo -e "Stopping ${BLUE}$server${NC}..."
        docker-compose stop "$server"
    done
    
    echo -e "${GREEN}Всі MCP сервери зупинені${NC}"
}

restart_servers() {
    echo -e "${YELLOW}Перезапускаю MCP сервери...${NC}"
    stop_servers
    echo
    start_servers
}

check_status() {
    echo -e "${YELLOW}Статус MCP серверів:${NC}"
    echo
    
    for server_port in $MCP_SERVERS; do
        local server=$(echo "$server_port" | cut -d: -f1)
        echo -e "Checking ${BLUE}$server${NC}..."
        docker-compose ps "$server" | tail -n +2
        echo
    done
}

check_health() {
    echo -e "${YELLOW}Перевірка health endpoints:${NC}"
    echo
    
    local all_healthy=true
    
    for server_port in $MCP_SERVERS; do
        local server=$(echo "$server_port" | cut -d: -f1)
        local port=$(echo "$server_port" | cut -d: -f2)
        local url="http://localhost:$port/health"
        
        echo -e "Checking ${BLUE}$server${NC} на порту ${BLUE}$port${NC}..."
        
        if curl -s --max-time 5 "$url" >/dev/null 2>&1; then
            local health_response=$(curl -s --max-time 5 "$url" | jq . 2>/dev/null || curl -s --max-time 5 "$url")
            echo -e "${GREEN}✓ Healthy${NC}: $health_response"
        else
            echo -e "${RED}✗ Not responding${NC}"
            all_healthy=false
        fi
        echo
    done
    
    if $all_healthy; then
        echo -e "${GREEN}Всі MCP сервери працюють нормально!${NC}"
    else
        echo -e "${RED}Деякі сервери не відповідають. Перевірте логи.${NC}"
        return 1
    fi
}

show_logs() {
    echo -e "${YELLOW}Логи MCP серверів:${NC}"
    echo
    
    if [ $# -eq 2 ]; then
        local specific_server="$2"
        echo -e "Логи для ${BLUE}$specific_server${NC}:"
        docker-compose logs --tail=50 "$specific_server"
    else
        for server_port in $MCP_SERVERS; do
            local server=$(echo "$server_port" | cut -d: -f1)
            echo -e "${BLUE}=== Логи $server ===${NC}"
            docker-compose logs --tail=20 "$server"
            echo
        done
    fi
}

build_images() {
    echo -e "${YELLOW}Пересборка MCP образів...${NC}"
    echo
    
    for server_port in $MCP_SERVERS; do
        local server=$(echo "$server_port" | cut -d: -f1)
        echo -e "Building ${BLUE}$server${NC}..."
        docker-compose build "$server"
        echo
    done
    
    echo -e "${GREEN}Всі образи пересібрані${NC}"
}

main() {
    print_header
    
    case "${1:-}" in
        start)
            start_servers
            ;;
        stop)
            stop_servers
            ;;
        restart)
            restart_servers
            ;;
        status)
            check_status
            ;;
        health)
            check_health
            ;;
        logs)
            show_logs "$@"
            ;;
        build)
            build_images
            ;;
        *)
            print_usage
            exit 1
            ;;
    esac
}

# Перевірка залежностей
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}docker-compose не знайдено. Встановіть Docker Compose.${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}jq не знайдено. JSON вивід буде неформатованим.${NC}"
fi

main "$@"
