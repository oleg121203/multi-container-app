"""
Playwright MCP Server - Browser automation service

Provides a secure, containerized browser automation service using Playwright
with proper isolation and resource limits.
"""

import asyncio
import logging
import json
import base64
import os
import tempfile
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import uvicorn

logger = logging.getLogger(__name__)


class ActionRequest(BaseModel):
    """Request model for MCP action execution"""
    action: str
    args: Dict[str, Any]
    correlation_id: Optional[str] = None


class ActionResponse(BaseModel):
    """Response model for MCP action execution"""
    status: str
    result: Any = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class PlaywrightMCPServer:
    """Playwright MCP Server for browser automation"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Playwright MCP Server",
            description="Browser automation service with security isolation",
            version="1.0.0"
        )
        self.playwright = None
        self.browser = None
        self.setup_routes()
        
        # Browser configuration
        self.browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ]
        
        # Security settings
        self.allowed_domains = self._get_allowed_domains()
        self.max_pages = int(os.getenv('PLAYWRIGHT_MAX_PAGES', '5'))
        self.page_timeout = int(os.getenv('PLAYWRIGHT_PAGE_TIMEOUT', '30000'))
        
    def _get_allowed_domains(self) -> List[str]:
        """Get list of allowed domains from environment"""
        domains_env = os.getenv('PLAYWRIGHT_ALLOWED_DOMAINS', '')
        if domains_env:
            return [domain.strip() for domain in domains_env.split(',')]
        return []  # Allow all if not specified
    
    async def start(self):
        """Start the Playwright browser"""
        logger.info("Starting Playwright MCP Server")
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=self.browser_args
        )
        
        logger.info("Playwright browser started")
    
    async def stop(self):
        """Stop the Playwright browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright MCP Server stopped")
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "ok", "service": "playwright-mcp"}
        
        @self.app.get("/capabilities")
        async def get_capabilities():
            """Get server capabilities"""
            return {
                "capabilities": [
                    "browser_navigation",
                    "page_screenshot",
                    "element_interaction",
                    "content_extraction",
                    "form_submission"
                ],
                "actions": [
                    "navigate_to_url",
                    "take_screenshot",
                    "get_page_content",
                    "click_element",
                    "fill_form",
                    "extract_text",
                    "wait_for_element"
                ]
            }
        
        @self.app.post("/execute")
        async def execute_action(request: ActionRequest):
            """Execute a browser automation action"""
            try:
                result = await self._execute_action(
                    request.action,
                    request.args,
                    request.correlation_id
                )
                
                return ActionResponse(
                    status="success",
                    result=result,
                    metrics={"execution_time_ms": 0}  # TODO: Add timing
                )
                
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                return ActionResponse(
                    status="failed",
                    error=str(e)
                )
    
    async def _execute_action(self, action: str, args: Dict[str, Any], correlation_id: Optional[str]) -> Any:
        """Execute a specific browser action"""
        logger.info(f"Executing action: {action} [correlation_id: {correlation_id}]")
        
        # Create new browser context for each action (security isolation)
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            ignore_https_errors=True
        )
        
        try:
            if action == "navigate_to_url":
                return await self._navigate_to_url(context, args)
            elif action == "take_screenshot":
                return await self._take_screenshot(context, args)
            elif action == "get_page_content":
                return await self._get_page_content(context, args)
            elif action == "click_element":
                return await self._click_element(context, args)
            elif action == "fill_form":
                return await self._fill_form(context, args)
            elif action == "extract_text":
                return await self._extract_text(context, args)
            elif action == "wait_for_element":
                return await self._wait_for_element(context, args)
            else:
                raise ValueError(f"Unsupported action: {action}")
                
        finally:
            await context.close()
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL against allowed domains"""
        if not self.allowed_domains:
            return True  # Allow all if no restrictions
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        for allowed in self.allowed_domains:
            if domain == allowed.lower() or domain.endswith('.' + allowed.lower()):
                return True
        
        return False
    
    async def _navigate_to_url(self, context: BrowserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Navigate to a URL"""
        url = args.get('url')
        if not url:
            raise ValueError("URL is required")
        
        if not self._validate_url(url):
            raise ValueError(f"URL not allowed: {url}")
        
        page = await context.new_page()
        
        try:
            response = await page.goto(url, timeout=self.page_timeout)
            title = await page.title()
            
            return {
                "url": url,
                "title": title,
                "status_code": response.status if response else None,
                "final_url": page.url
            }
        finally:
            await page.close()
    
    async def _take_screenshot(self, context: BrowserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Take a screenshot of a page"""
        url = args.get('url')
        if not url:
            raise ValueError("URL is required")
        
        if not self._validate_url(url):
            raise ValueError(f"URL not allowed: {url}")
        
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=self.page_timeout)
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Take screenshot
            screenshot_bytes = await page.screenshot(
                full_page=args.get('full_page', False),
                type='png'
            )
            
            # Encode as base64
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            return {
                "url": url,
                "title": await page.title(),
                "screenshot": screenshot_b64,
                "format": "png"
            }
        finally:
            await page.close()
    
    async def _get_page_content(self, context: BrowserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get page content"""
        url = args.get('url')
        if not url:
            raise ValueError("URL is required")
        
        if not self._validate_url(url):
            raise ValueError(f"URL not allowed: {url}")
        
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=self.page_timeout)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            content = await page.content()
            text = await page.inner_text('body')
            title = await page.title()
            
            return {
                "url": url,
                "title": title,
                "html_content": content,
                "text_content": text
            }
        finally:
            await page.close()
    
    async def _click_element(self, context: BrowserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Click an element on the page"""
        url = args.get('url')
        selector = args.get('selector')
        
        if not url:
            raise ValueError("URL is required")
        if not selector:
            raise ValueError("Selector is required")
        
        if not self._validate_url(url):
            raise ValueError(f"URL not allowed: {url}")
        
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=self.page_timeout)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Wait for element to be visible
            await page.wait_for_selector(selector, timeout=10000)
            
            # Click the element
            await page.click(selector)
            
            # Wait a bit for any navigation or changes
            await page.wait_for_timeout(1000)
            
            return {
                "url": url,
                "selector": selector,
                "final_url": page.url,
                "success": True
            }
        finally:
            await page.close()
    
    async def _fill_form(self, context: BrowserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Fill a form on the page"""
        url = args.get('url')
        form_data = args.get('form_data', {})
        
        if not url:
            raise ValueError("URL is required")
        if not form_data:
            raise ValueError("Form data is required")
        
        if not self._validate_url(url):
            raise ValueError(f"URL not allowed: {url}")
        
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=self.page_timeout)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Fill form fields
            for selector, value in form_data.items():
                await page.wait_for_selector(selector, timeout=5000)
                await page.fill(selector, str(value))
            
            return {
                "url": url,
                "form_data_filled": len(form_data),
                "success": True
            }
        finally:
            await page.close()
    
    async def _extract_text(self, context: BrowserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from specific elements"""
        url = args.get('url')
        selectors = args.get('selectors', [])
        
        if not url:
            raise ValueError("URL is required")
        if not selectors:
            raise ValueError("Selectors are required")
        
        if not self._validate_url(url):
            raise ValueError(f"URL not allowed: {url}")
        
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=self.page_timeout)
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            extracted_data = {}
            
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    texts = []
                    for element in elements[:10]:  # Limit to 10 elements
                        text = await element.inner_text()
                        texts.append(text.strip())
                    extracted_data[selector] = texts
                except Exception as e:
                    extracted_data[selector] = f"Error: {str(e)}"
            
            return {
                "url": url,
                "extracted_data": extracted_data
            }
        finally:
            await page.close()
    
    async def _wait_for_element(self, context: BrowserContext, args: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for an element to appear"""
        url = args.get('url')
        selector = args.get('selector')
        timeout = args.get('timeout', 10000)
        
        if not url:
            raise ValueError("URL is required")
        if not selector:
            raise ValueError("Selector is required")
        
        if not self._validate_url(url):
            raise ValueError(f"URL not allowed: {url}")
        
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=self.page_timeout)
            
            # Wait for the element
            element = await page.wait_for_selector(selector, timeout=timeout)
            element_text = await element.inner_text() if element else ""
            
            return {
                "url": url,
                "selector": selector,
                "found": element is not None,
                "text": element_text
            }
        finally:
            await page.close()


# Global server instance
playwright_server = PlaywrightMCPServer()


async def main():
    """Main entry point for the Playwright MCP server"""
    import signal
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start the server
    await playwright_server.start()
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(playwright_server.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start HTTP server
    config = uvicorn.Config(
        playwright_server.app,
        host="0.0.0.0",
        port=int(os.getenv('MCP_PORT', '4001')),
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    finally:
        await playwright_server.stop()


if __name__ == "__main__":
    asyncio.run(main())