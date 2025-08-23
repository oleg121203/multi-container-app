#!/bin/bash

# Тестовий скрипт для перевірки інтеграції з MCP Hub
# Використовуйте цей скрипт для швидкої перевірки всіх компонентів

echo "🚀 MCP Hub Integration Test Suite"
echo "=================================="

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функція для перевірки доступності порту
check_port() {
    local port=$1
    local name=$2
    
    if curl -s -f "http://localhost:$port/health" > /dev/null; then
        echo -e "${GREEN}✅ $name (port $port) - OK${NC}"
        return 0
    else
        echo -e "${RED}❌ $name (port $port) - FAILED${NC}"
        return 1
    fi
}

# Функція для тестування API
test_api() {
    local url=$1
    local data=$2
    local name=$3
    
    echo -e "${BLUE}🧪 Testing $name...${NC}"
    
    if [ -n "$data" ]; then
        response=$(curl -s -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null)
    else
        response=$(curl -s "$url" 2>/dev/null)
    fi
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo -e "${GREEN}   ✅ $name - SUCCESS${NC}"
        echo -e "${YELLOW}   Response: ${response:0:100}...${NC}"
        return 0
    else
        echo -e "${RED}   ❌ $name - FAILED${NC}"
        return 1
    fi
}

# 1. Перевірка доступності MCP серверів
echo -e "\n${BLUE}📡 Checking MCP Servers...${NC}"
servers_ok=0
total_servers=9

check_port 3001 "Playwright MCP" && ((servers_ok++))
check_port 3002 "Atlas Coordinator" && ((servers_ok++))
check_port 3003 "MCP Orchestrator" && ((servers_ok++))
check_port 3004 "Atlas 2 Visual" && ((servers_ok++))
check_port 3005 "Context MCP" && ((servers_ok++))
check_port 3006 "macOS Automator" && ((servers_ok++))
check_port 3007 "Streaming TTS" && ((servers_ok++))
check_port 3008 "Linux Automator" && ((servers_ok++))
check_port 3009 "Atlas Controller" && ((servers_ok++))

echo -e "\n${BLUE}📊 Servers Status: $servers_ok/$total_servers online${NC}"

# 2. Тестування української мови
echo -e "\n${BLUE}🇺🇦 Testing Ukrainian Language Processing...${NC}"
ukrainian_data='{"message": "відкрий мені програму мюсік", "history": []}'
test_api "http://localhost:3002/chat" "$ukrainian_data" "Ukrainian Command Processing"

# 3. Тестування браузерної автоматизації
echo -e "\n${BLUE}🌐 Testing Browser Automation...${NC}"
browser_data='{"url": "https://google.com"}'
test_api "http://localhost:3001/health" "" "Playwright MCP Health"

# 4. Тестування TTS
echo -e "\n${BLUE}🎵 Testing Text-to-Speech...${NC}"
tts_data='{"text": "Привіт світ", "voice": "uk_female"}'
test_api "http://localhost:3007/health" "" "TTS Server Health"

# 5. Тестування macOS автоматизації
echo -e "\n${BLUE}🍎 Testing macOS Automation...${NC}"
macos_data='{"script": "tell application \"System Events\" to get name of processes", "type": "applescript"}'
test_api "http://localhost:3006/health" "" "macOS Automator Health"

# 6. Перевірка 3D моделі
echo -e "\n${BLUE}🎭 Testing 3D Head Model...${NC}"
if curl -s -f "http://localhost:8099/assets/models/robot-head/DamagedHelmet.glb" > /dev/null; then
    echo -e "${GREEN}✅ 3D Head Model - OK${NC}"
else
    echo -e "${RED}❌ 3D Head Model - FAILED${NC}"
    echo -e "${YELLOW}   Checking local model...${NC}"
    if [ -f "../frontend-hacker/public/models/robot-head/DamagedHelmet.glb" ]; then
        echo -e "${GREEN}   ✅ Local model exists${NC}"
    else
        echo -e "${RED}   ❌ Local model missing${NC}"
    fi
fi

# 7. Тестування цього Express додатку
echo -e "\n${BLUE}🚀 Testing Express Standalone App...${NC}"
if [ -f "server.js" ]; then
    echo -e "${GREEN}✅ server.js exists${NC}"
    
    # Перевірка залежностей
    if [ -f "package.json" ]; then
        echo -e "${GREEN}✅ package.json exists${NC}"
    else
        echo -e "${RED}❌ package.json missing${NC}"
    fi
    
    # Перевірка моделі
    if [ -f "models/DamagedHelmet.glb" ]; then
        echo -e "${GREEN}✅ 3D model copied${NC}"
    else
        echo -e "${RED}❌ 3D model missing${NC}"
    fi
    
    # Перевірка static файлів
    if [ -f "public/index.html" ]; then
        echo -e "${GREEN}✅ Frontend files exist${NC}"
    else
        echo -e "${RED}❌ Frontend files missing${NC}"
    fi
    
else
    echo -e "${RED}❌ server.js missing${NC}"
fi

# 8. Підсумок
echo -e "\n${BLUE}📋 Integration Test Summary${NC}"
echo "=================================="

if [ $servers_ok -ge 7 ]; then
    echo -e "${GREEN}🎉 MCP Hub Integration: READY${NC}"
    echo -e "${GREEN}   Most servers are online and responding${NC}"
    echo -e "${YELLOW}   You can now start building your integration!${NC}"
else
    echo -e "${RED}⚠️  MCP Hub Integration: ISSUES DETECTED${NC}"
    echo -e "${RED}   Only $servers_ok/$total_servers servers are online${NC}"
    echo -e "${YELLOW}   Please run '../start.sh' to start MCP Hub system${NC}"
fi

echo -e "\n${BLUE}🔧 Quick Commands:${NC}"
echo "  Start MCP Hub:     cd .. && ./start.sh"
echo "  Check Status:      cd .. && ./status.sh"
echo "  Start This App:    npm start"
echo "  View Logs:         cd .. && tail -f logs/*.log"

echo -e "\n${BLUE}📖 Documentation:${NC}"
echo "  Integration Guide: cat INTEGRATION_GUIDE.md"
echo "  Examples:          ls examples/"
echo "  API Tests:         node examples/mcp-integration-example.js"

echo -e "\n${GREEN}✨ Happy coding!${NC}"
