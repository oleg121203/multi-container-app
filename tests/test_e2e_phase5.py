#!/usr/bin/env python3
"""
ATLAS Phase 5 End-to-End Testing Suite

Comprehensive E2E testing for the enhanced web interface and backend integration.
Tests all Phase 5 features including voice capabilities, advanced team management,
performance monitoring, and error recovery.
"""

import asyncio
import json
import requests
import time
import websockets
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ATLASE2ETestSuite:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws") + "/ws"
        self.session = requests.Session()
        self.test_results = []
        
    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        logger.info(f"[{status}] {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message,
            "timestamp": time.time()
        })
        
    async def run_all_tests(self):
        """Run complete E2E test suite"""
        logger.info("🚀 Starting ATLAS Phase 5 E2E Test Suite")
        logger.info("=" * 60)
        
        # Core API Tests
        await self.test_health_endpoint()
        await self.test_agents_api()
        await self.test_system_status()
        await self.test_metrics_api()
        
        # Enhanced API Tests  
        await self.test_team_formation_enhanced()
        await self.test_analytics_endpoint()
        await self.test_diagnostics_endpoint()
        await self.test_voice_apis()
        
        # WebSocket Tests
        await self.test_websocket_connection()
        await self.test_websocket_messaging()
        
        # Integration Tests
        await self.test_team_workflow()
        await self.test_error_handling()
        
        # Performance Tests
        await self.test_api_performance()
        
        self.print_test_summary()
        
    async def test_health_endpoint(self):
        """Test basic health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            data = response.json()
            
            passed = response.status_code == 200 and data.get("status") == "healthy"
            self.log_test_result("Health Endpoint", passed, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test_result("Health Endpoint", False, str(e))
            
    async def test_agents_api(self):
        """Test agents API endpoints"""
        try:
            # Test GET /api/agents
            response = self.session.get(f"{self.base_url}/api/agents", timeout=5)
            data = response.json()
            
            agents_loaded = response.status_code == 200 and "agents" in data
            self.log_test_result("Agents API - List", agents_loaded, f"Found {len(data.get('agents', []))} agents")
            
            # Test individual agent status if agents exist
            if agents_loaded and data.get("agents"):
                agent_id = data["agents"][0].get("id", data["agents"][0].get("name"))
                status_response = self.session.get(f"{self.base_url}/api/agents/{agent_id}/status", timeout=5)
                status_ok = status_response.status_code == 200
                self.log_test_result("Agents API - Status", status_ok, f"Agent {agent_id} status")
                
        except Exception as e:
            self.log_test_result("Agents API", False, str(e))
            
    async def test_system_status(self):
        """Test system status endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/system/status", timeout=5)
            data = response.json()
            
            passed = response.status_code == 200 and len(data) > 0
            self.log_test_result("System Status", passed, f"Services: {list(data.keys())}")
        except Exception as e:
            self.log_test_result("System Status", False, str(e))
            
    async def test_metrics_api(self):
        """Test metrics endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/api/metrics", timeout=5)
            data = response.json()
            
            required_metrics = ["active_agents", "teams_formed", "tasks_completed"]
            has_metrics = all(metric in data for metric in required_metrics)
            
            self.log_test_result("Metrics API", has_metrics, f"Metrics: {list(data.keys())}")
        except Exception as e:
            self.log_test_result("Metrics API", False, str(e))
            
    async def test_team_formation_enhanced(self):
        """Test enhanced team formation"""
        try:
            team_request = {
                "description": "E2E Test: Create a test monitoring system",
                "constraints": {
                    "teamSize": 3,
                    "priority": "high"
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/teams/form", 
                json=team_request, 
                timeout=10
            )
            data = response.json()
            
            team_formed = response.status_code == 200 and "team" in data
            self.log_test_result("Enhanced Team Formation", team_formed, 
                               f"Team members: {len(data.get('team', {}).get('members', []))}")
                               
        except Exception as e:
            self.log_test_result("Enhanced Team Formation", False, str(e))
            
    async def test_analytics_endpoint(self):
        """Test analytics data submission"""
        try:
            analytics_data = {
                "pageViews": 1,
                "interactions": 5,
                "sessionStart": time.time() * 1000,
                "features": {
                    "voiceCommands": 2,
                    "teamsFormed": 1,
                    "agentInteractions": 3
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/analytics",
                json=analytics_data,
                timeout=5
            )
            
            passed = response.status_code == 200
            self.log_test_result("Analytics Endpoint", passed, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test_result("Analytics Endpoint", False, str(e))
            
    async def test_diagnostics_endpoint(self):
        """Test system diagnostics"""
        try:
            response = self.session.get(f"{self.base_url}/api/diagnostics", timeout=5)
            data = response.json()
            
            has_diagnostics = response.status_code == 200 and "system" in data
            self.log_test_result("Diagnostics API", has_diagnostics, 
                               f"Sections: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
        except Exception as e:
            self.log_test_result("Diagnostics API", False, str(e))
            
    async def test_voice_apis(self):
        """Test voice interaction APIs"""
        try:
            # Test TTS endpoint
            tts_request = {
                "text": "Hello from ATLAS E2E test",
                "voice": "atlas",
                "agent_id": "atlas"
            }
            
            tts_response = self.session.post(
                f"{self.base_url}/api/tts",
                json=tts_request,
                timeout=5
            )
            
            tts_ok = tts_response.status_code == 200
            self.log_test_result("TTS API", tts_ok, f"Status: {tts_response.status_code}")
            
            # Test voices endpoint
            voices_response = self.session.get(f"{self.base_url}/api/voices", timeout=5)
            voices_data = voices_response.json()
            
            voices_ok = voices_response.status_code == 200 and "voices" in voices_data
            self.log_test_result("Voices API", voices_ok, 
                               f"Available voices: {len(voices_data.get('voices', []))}")
                               
        except Exception as e:
            self.log_test_result("Voice APIs", False, str(e))
            
    async def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            async with websockets.connect(self.ws_url, timeout=10) as websocket:
                # Wait for welcome message
                welcome = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome)
                
                connected = welcome_data.get("type") == "system"
                self.log_test_result("WebSocket Connection", connected, "Connected successfully")
                
        except Exception as e:
            self.log_test_result("WebSocket Connection", False, str(e))
            
    async def test_websocket_messaging(self):
        """Test WebSocket messaging"""
        try:
            async with websockets.connect(self.ws_url, timeout=10) as websocket:
                # Skip welcome message
                await websocket.recv()
                
                # Send test message
                test_message = {
                    "type": "chat",
                    "message": "E2E test message",
                    "timestamp": "2024-08-22T20:30:00Z"
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                
                message_ok = response_data.get("type") == "chat"
                self.log_test_result("WebSocket Messaging", message_ok, "Message echo received")
                
        except Exception as e:
            self.log_test_result("WebSocket Messaging", False, str(e))
            
    async def test_team_workflow(self):
        """Test complete team formation workflow"""
        try:
            # Step 1: Form team
            team_request = {
                "description": "E2E Workflow Test: Build secure API",
                "constraints": {"priority": "normal"}
            }
            
            team_response = self.session.post(
                f"{self.base_url}/api/teams/form",
                json=team_request,
                timeout=10
            )
            
            # Step 2: Check team history
            history_response = self.session.get(f"{self.base_url}/api/teams/history", timeout=5)
            
            # Step 3: Get system status
            status_response = self.session.get(f"{self.base_url}/api/system/status", timeout=5)
            
            workflow_ok = all([
                team_response.status_code == 200,
                history_response.status_code == 200,
                status_response.status_code == 200
            ])
            
            self.log_test_result("Team Workflow", workflow_ok, "Complete workflow executed")
            
        except Exception as e:
            self.log_test_result("Team Workflow", False, str(e))
            
    async def test_error_handling(self):
        """Test error handling and recovery"""
        try:
            # Test invalid agent ID
            response = self.session.get(f"{self.base_url}/api/agents/invalid_agent/status", timeout=5)
            error_handled = response.status_code in [404, 200]  # Should handle gracefully
            
            # Test invalid team formation
            invalid_team_request = {"description": ""}  # Empty description
            team_response = self.session.post(
                f"{self.base_url}/api/teams/form",
                json=invalid_team_request,
                timeout=5
            )
            
            team_error_handled = team_response.status_code in [400, 200]  # Should handle gracefully
            
            error_ok = error_handled and team_error_handled
            self.log_test_result("Error Handling", error_ok, "Invalid requests handled gracefully")
            
        except Exception as e:
            self.log_test_result("Error Handling", False, str(e))
            
    async def test_api_performance(self):
        """Test API performance and response times"""
        try:
            start_time = time.time()
            
            # Make multiple concurrent requests
            responses = []
            for _ in range(10):
                response = self.session.get(f"{self.base_url}/api/agents", timeout=2)
                responses.append(response)
                
            end_time = time.time()
            total_time = end_time - start_time
            avg_time = total_time / len(responses)
            
            all_successful = all(r.status_code == 200 for r in responses)
            performance_ok = all_successful and avg_time < 1.0  # Less than 1 second average
            
            self.log_test_result("API Performance", performance_ok, 
                               f"10 requests in {total_time:.2f}s (avg: {avg_time:.2f}s)")
                               
        except Exception as e:
            self.log_test_result("API Performance", False, str(e))
            
    def print_test_summary(self):
        """Print comprehensive test summary"""
        passed_tests = [r for r in self.test_results if r["passed"]]
        failed_tests = [r for r in self.test_results if not r["passed"]]
        
        logger.info("=" * 60)
        logger.info("🎯 ATLAS Phase 5 E2E Test Results Summary")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {len(self.test_results)}")
        logger.info(f"✅ Passed: {len(passed_tests)}")
        logger.info(f"❌ Failed: {len(failed_tests)}")
        logger.info(f"📊 Success Rate: {len(passed_tests)/len(self.test_results)*100:.1f}%")
        
        if failed_tests:
            logger.info("\n❌ Failed Tests:")
            for test in failed_tests:
                logger.info(f"  - {test['test']}: {test['message']}")
                
        if len(passed_tests) == len(self.test_results):
            logger.info("\n🎉 All tests passed! Phase 5 is ready for production.")
        else:
            logger.info(f"\n⚠️  {len(failed_tests)} tests failed. Please review and fix issues.")
            
        # Save results to file
        with open(f"e2e-test-results-{int(time.time())}.json", "w") as f:
            json.dump(self.test_results, f, indent=2)

async def main():
    """Main test execution"""
    suite = ATLASE2ETestSuite()
    await suite.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())