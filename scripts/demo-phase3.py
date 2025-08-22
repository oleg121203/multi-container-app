#!/usr/bin/env python3
"""
Phase 3 Demo Script - ATLAS MCP Hub, Security, and Browser Automation

This script demonstrates the Phase 3 functionality including:
- MCP Hub service discovery and execution
- Playwright browser automation
- LLM3 security monitoring with Falco integration
- TTS/STT voice capabilities

Note: This demo script requires the Phase 3 services to be running.
Run './scripts/setup-phase3.sh' first to start all services.
"""

import asyncio
import json
import time
import logging
import os
from typing import Dict, Any

# Check for aiohttp availability
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("⚠️  Warning: aiohttp not available. Install with: pip install aiohttp")
    print("Running in limited mode without HTTP client functionality.")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Phase3Demo:
    """Demo runner for Phase 3 ATLAS functionality"""
    
    def __init__(self):
        self.base_urls = {
            'llm1': 'http://localhost:8001',
            'llm2': 'http://localhost:8002', 
            'llm3': 'http://localhost:8003',
            'playwright_mcp': 'http://localhost:4001',
            'tts_mcp': 'http://localhost:4004',
            'stt_mcp': 'http://localhost:8080'
        }
        
    async def run_demo(self):
        """Run the complete Phase 3 demo"""
        logger.info("🚀 Starting ATLAS Phase 3 Demo")
        
        if not HAS_AIOHTTP:
            logger.warning("Running in limited mode due to missing aiohttp dependency")
            await self.demo_limited_mode()
            return
        
        try:
            # Test service health
            await self.test_service_health()
            
            # Test MCP Hub functionality
            await self.demo_mcp_hub()
            
            # Test Playwright automation
            await self.demo_playwright_automation()
            
            # Test LLM3 security monitoring
            await self.demo_security_monitoring()
            
            # Test TTS/STT capabilities
            await self.demo_voice_capabilities()
            
            # Test end-to-end scenario
            await self.demo_e2e_scenario()
            
            logger.info("✅ Phase 3 Demo completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            raise
    
    async def test_service_health(self):
        """Test health of all Phase 3 services"""
        logger.info("\n🔍 Testing service health...")
        
        async with aiohttp.ClientSession() as session:
            for service, url in self.base_urls.items():
                try:
                    async with session.get(f"{url}/health") as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"✅ {service}: {data.get('status', 'ok')}")
                        else:
                            logger.warning(f"⚠️  {service}: HTTP {response.status}")
                except Exception as e:
                    logger.error(f"❌ {service}: {e}")
    
    async def demo_mcp_hub(self):
        """Demonstrate MCP Hub functionality"""
        logger.info("\n🔧 Demonstrating MCP Hub...")
        
        async with aiohttp.ClientSession() as session:
            # Get MCP server status
            try:
                async with session.get(f"{self.base_urls['llm2']}/mcp/servers") as response:
                    if response.status == 200:
                        servers = await response.json()
                        logger.info(f"📋 MCP Servers registered: {servers.get('total_servers', 0)}")
                        for name, info in servers.get('servers', {}).items():
                            logger.info(f"  • {name}: {info['status']} ({info['url']})")
                    else:
                        logger.warning(f"Failed to get MCP servers: HTTP {response.status}")
            except Exception as e:
                logger.error(f"MCP Hub demo error: {e}")
            
            # Get available capabilities
            try:
                async with session.get(f"{self.base_urls['llm2']}/mcp/capabilities") as response:
                    if response.status == 200:
                        capabilities = await response.json()
                        logger.info("🛠️  Available MCP capabilities:")
                        for server, caps in capabilities.items():
                            logger.info(f"  • {server}: {', '.join(caps)}")
            except Exception as e:
                logger.error(f"Capabilities demo error: {e}")
    
    async def demo_playwright_automation(self):
        """Demonstrate Playwright MCP browser automation"""
        logger.info("\n🌐 Demonstrating Playwright automation...")
        
        async with aiohttp.ClientSession() as session:
            # Test direct Playwright MCP call
            try:
                # Take a screenshot of a webpage
                screenshot_request = {
                    "action": "take_screenshot",
                    "args": {
                        "url": "https://httpbin.org/html",
                        "full_page": False
                    }
                }
                
                async with session.post(
                    f"{self.base_urls['playwright_mcp']}/execute",
                    json=screenshot_request
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("📸 Screenshot taken successfully")
                        logger.info(f"  • Page title: {result.get('result', {}).get('title', 'N/A')}")
                        logger.info(f"  • Screenshot format: {result.get('result', {}).get('format', 'N/A')}")
                    else:
                        logger.warning(f"Screenshot failed: HTTP {response.status}")
            except Exception as e:
                logger.error(f"Playwright demo error: {e}")
            
            # Test via LLM2 MCP Hub
            try:
                mcp_request = {
                    "action": "navigate_to_url",
                    "args": {"url": "https://httpbin.org/json"},
                    "server_preference": "playwright"
                }
                
                async with session.post(
                    f"{self.base_urls['llm2']}/mcp/execute",
                    json=mcp_request
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("🔗 Navigation via MCP Hub successful")
                        logger.info(f"  • Server used: {result.get('server_used')}")
                        logger.info(f"  • Execution time: {result.get('execution_time_ms')}ms")
                    else:
                        logger.warning(f"MCP navigation failed: HTTP {response.status}")
            except Exception as e:
                logger.error(f"MCP Hub automation error: {e}")
    
    async def demo_security_monitoring(self):
        """Demonstrate LLM3 security monitoring"""
        logger.info("\n🛡️  Demonstrating security monitoring...")
        
        async with aiohttp.ClientSession() as session:
            # Send a test security event to LLM3
            try:
                test_event = {
                    "time": "2024-01-15T10:30:00Z",
                    "rule": "Write below etc",
                    "priority": "CRITICAL",
                    "output": "Detected write to /etc/passwd (demo event)",
                    "source": "falco",
                    "proc": {
                        "pid": 1234,
                        "cmdline": "/bin/sh -c echo demo > /etc/passwd"
                    },
                    "k8s": {
                        "pod_name": "demo-pod",
                        "namespace": "default",
                        "container_id": "docker://demo123"
                    }
                }
                
                async with session.post(
                    f"{self.base_urls['llm3']}/test-event",
                    json=test_event
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("🚨 Security event processed")
                        logger.info(f"  • Event ID: {result.get('event_id')}")
                    else:
                        logger.warning(f"Security event failed: HTTP {response.status}")
                
                # Wait a moment for processing
                await asyncio.sleep(2)
                
                # Check audit log
                async with session.get(f"{self.base_urls['llm3']}/audit-log?limit=5") as response:
                    if response.status == 200:
                        audit = await response.json()
                        logger.info(f"📝 Audit log entries: {len(audit.get('audit_log', []))}")
                        for entry in audit.get('audit_log', [])[:3]:
                            logger.info(f"  • {entry.get('rule')}: {entry.get('decision', {}).get('severity')}")
                    
            except Exception as e:
                logger.error(f"Security monitoring demo error: {e}")
    
    async def demo_voice_capabilities(self):
        """Demonstrate TTS/STT voice capabilities"""
        logger.info("\n🎙️  Demonstrating voice capabilities...")
        
        async with aiohttp.ClientSession() as session:
            # Test TTS capability
            try:
                async with session.get(f"{self.base_urls['tts_mcp']}/capabilities") as response:
                    if response.status == 200:
                        capabilities = await response.json()
                        logger.info("🔊 TTS capabilities available:")
                        for cap in capabilities.get('capabilities', []):
                            logger.info(f"  • {cap}")
                    else:
                        logger.warning(f"TTS capabilities check failed: HTTP {response.status}")
            except Exception as e:
                logger.error(f"TTS demo error: {e}")
            
            # Test STT capability
            try:
                async with session.get(f"{self.base_urls['stt_mcp']}/health") as response:
                    if response.status == 200:
                        logger.info("🎤 STT service is available")
                    else:
                        logger.warning(f"STT health check failed: HTTP {response.status}")
            except Exception as e:
                logger.error(f"STT demo error: {e}")
    
    async def demo_e2e_scenario(self):
        """Demonstrate end-to-end scenario"""
        logger.info("\n🔄 Demonstrating end-to-end scenario...")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Scenario: User asks LLM2 to take a screenshot and analyze security
                
                # Step 1: Task request to LLM2
                task_request = {
                    "description": "Take a screenshot of httpbin.org and check for security issues",
                    "requester_id": "demo_user",
                    "priority": "medium"
                }
                
                async with session.post(
                    f"{self.base_urls['llm2']}/process_task",
                    json=task_request
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info("📋 Task created successfully")
                        logger.info(f"  • Task ID: {result.get('task_id')}")
                        logger.info(f"  • Agent used: {result.get('agent_used')}")
                        if result.get('linear_issue'):
                            logger.info(f"  • Linear issue: {result['linear_issue'].get('title')}")
                    else:
                        logger.warning(f"Task creation failed: HTTP {response.status}")
                
                # Step 2: Simulate browser automation (would be triggered by LLM2)
                screenshot_request = {
                    "action": "take_screenshot",
                    "args": {"url": "https://httpbin.org", "full_page": True}
                }
                
                async with session.post(
                    f"{self.base_urls['llm2']}/mcp/execute",
                    json=screenshot_request
                ) as response:
                    if response.status == 200:
                        logger.info("📸 Screenshot automation completed")
                
                # Step 3: Simulate security monitoring (ongoing)
                logger.info("🛡️  Security monitoring active (background)")
                
                logger.info("✅ End-to-end scenario completed")
                
            except Exception as e:
                logger.error(f"E2E scenario error: {e}")
    
    async def generate_demo_report(self):
        """Generate a summary report of the demo"""
        logger.info("\n📊 Demo Summary Report")
        logger.info("=" * 50)
        
        if not HAS_AIOHTTP:
            logger.info("Report generation requires aiohttp dependency")
            logger.info("Install with: pip install aiohttp")
            return
        
        async with aiohttp.ClientSession() as session:
            # Collect service status
            services_status = {}
            for service, url in self.base_urls.items():
                try:
                    async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        services_status[service] = "✅ Online" if response.status == 200 else "⚠️  Issues"
                except:
                    services_status[service] = "❌ Offline"
            
            logger.info("Service Status:")
            for service, status in services_status.items():
                logger.info(f"  {service:15} {status}")
            
            # MCP Hub status
            try:
                async with session.get(f"{self.base_urls['llm2']}/mcp/servers") as response:
                    if response.status == 200:
                        servers = await response.json()
                        logger.info(f"\nMCP Hub: {servers.get('healthy_servers', 0)}/{servers.get('total_servers', 0)} servers healthy")
            except:
                logger.info("\nMCP Hub: Status unavailable")
            
            # Security monitoring status
            try:
                async with session.get(f"{self.base_urls['llm3']}/audit-log?limit=1") as response:
                    if response.status == 200:
                        audit = await response.json()
                        logger.info(f"Security: {audit.get('total_events', 0)} events processed")
            except:
                logger.info("Security: Status unavailable")
        
        logger.info("\n🎉 Phase 3 Demo Complete!")
        logger.info("Key Features Demonstrated:")
        logger.info("  • MCP Hub service registry and discovery")
        logger.info("  • Playwright browser automation")
        logger.info("  • LLM3 security event processing")
        logger.info("  • Voice capabilities (TTS/STT)")
        logger.info("  • End-to-end orchestration")

    async def demo_limited_mode(self):
        """Demo functionality without aiohttp dependency"""
        logger.info("\n📋 Phase 3 Demo - Limited Mode")
        logger.info("=" * 50)
        
        logger.info("\n🏗️  Phase 3 Architecture Overview:")
        logger.info("  • MCP-01: MCP Hub for service orchestration")
        logger.info("  • GUI-01: Playwright automation for browser interaction")
        logger.info("  • SEC-01: LLM3 security monitoring with Falco integration")
        logger.info("  • MCP-05/06: Voice capabilities with TTS/STT")
        
        logger.info("\n📊 Service Configuration:")
        for service, url in self.base_urls.items():
            logger.info(f"  • {service}: {url}")
        
        logger.info("\n🔧 To run full demo:")
        logger.info("  1. Install dependencies: pip install aiohttp")
        logger.info("  2. Start services: ./scripts/setup-phase3.sh")
        logger.info("  3. Run demo: python scripts/demo-phase3.py")
        
        logger.info("\n✅ Phase 3 components are implemented and ready for testing")


async def main():
    """Main demo runner"""
    demo = Phase3Demo()
    
    try:
        await demo.run_demo()
        await demo.generate_demo_report()
    except KeyboardInterrupt:
        logger.info("\n⏹️  Demo interrupted by user")
    except Exception as e:
        logger.error(f"\n💥 Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))