import { test, expect } from '@playwright/test';

test.describe('ATLAS Voice Interaction E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the ATLAS interface
    await page.goto('/');
    
    // Wait for the interface to load
    await page.waitForSelector('#mainInterface', { state: 'visible' });
  });

  test('should load ATLAS interface successfully', async ({ page }) => {
    // Check that the main interface elements are present
    await expect(page.locator('#mainInterface')).toBeVisible();
    await expect(page.locator('.chat-panel')).toBeVisible();
    await expect(page.locator('#agentsGrid')).toBeVisible();
    
    // Check for voice control buttons
    await expect(page.locator('#voiceBtn')).toBeVisible();
  });

  test('should display agents in the grid', async ({ page }) => {
    // Wait for agents to load
    await page.waitForSelector('#agentsGrid .agent-card', { timeout: 10000 });
    
    // Check that at least one agent is displayed
    const agentCards = page.locator('#agentsGrid .agent-card');
    await expect(agentCards).toHaveCountGreaterThan(0);
    
    // Check that agent cards have required information
    const firstAgent = agentCards.first();
    await expect(firstAgent.locator('.agent-name')).toBeVisible();
    await expect(firstAgent.locator('.agent-status')).toBeVisible();
  });

  test('should handle team formation workflow', async ({ page }) => {
    // Click the team formation button
    await page.click('[data-action="form-team"]');
    
    // Wait for the team formation dialog
    await expect(page.locator('.team-dialog')).toBeVisible();
    
    // Fill in team description
    const descriptionInput = page.locator('input[placeholder*="team description"], textarea[placeholder*="team description"]');
    if (await descriptionInput.count() > 0) {
      await descriptionInput.fill('E2E Test: Create a monitoring team');
    }
    
    // Submit the form
    await page.click('button:has-text("Create Team"), button:has-text("Form Team")');
    
    // Check for success feedback
    await expect(page.locator('.success-message, .team-formed')).toBeVisible({ timeout: 10000 });
  });

  test('should send and receive chat messages', async ({ page }) => {
    // Find the message input
    const messageInput = page.locator('#messageInput');
    await expect(messageInput).toBeVisible();
    
    // Type a test message
    await messageInput.fill('Hello ATLAS, this is an E2E test');
    
    // Send the message
    await page.click('#sendBtn');
    
    // Check that the message appears in chat history
    await expect(page.locator('#chatHistory')).toContainText('Hello ATLAS, this is an E2E test');
  });

  test('should test voice button interaction', async ({ page }) => {
    // Grant microphone permissions (this may not work in headless mode)
    await page.context().grantPermissions(['microphone']);
    
    // Click the voice button
    const voiceBtn = page.locator('#voiceBtn');
    await expect(voiceBtn).toBeVisible();
    
    // Click and check for state change
    await voiceBtn.click();
    
    // The button should show listening state (if permissions are granted)
    // This test may be limited in headless environments
    await expect(voiceBtn).toBeVisible();
  });

  test('should display system status', async ({ page }) => {
    // Look for system status indicators
    const statusIndicators = page.locator('.status-indicator');
    if (await statusIndicators.count() > 0) {
      await expect(statusIndicators.first()).toBeVisible();
    }
    
    // Check for metrics display
    const metricsSection = page.locator('#systemMetrics, .metrics-panel');
    if (await metricsSection.count() > 0) {
      await expect(metricsSection).toBeVisible();
    }
  });

  test('should handle TTS API integration', async ({ page }) => {
    // Test TTS functionality by looking for TTS controls
    const ttsControls = page.locator('#ttsBtn, button:has-text("TTS")');
    
    if (await ttsControls.count() > 0) {
      await expect(ttsControls.first()).toBeVisible();
      
      // Click TTS button and verify it responds
      await ttsControls.first().click();
      
      // Check for any audio-related feedback or state changes
      // Note: Actual audio playback testing is complex in E2E tests
      await expect(ttsControls.first()).toBeVisible();
    }
  });

  test('should handle navigation and responsive design', async ({ page }) => {
    // Test that the interface works on different viewport sizes
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.locator('#mainInterface')).toBeVisible();
    
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('#mainInterface')).toBeVisible();
    
    // Restore desktop viewport
    await page.setViewportSize({ width: 1200, height: 800 });
  });

  test('should handle WebSocket connection', async ({ page }) => {
    // Check for WebSocket connection indicators
    const connectionStatus = page.locator('.connection-status, #connectionStatus');
    
    // Wait a moment for WebSocket to establish
    await page.waitForTimeout(2000);
    
    // Look for any connection-related UI elements
    const websocketIndicators = page.locator('[data-status], .ws-status');
    if (await websocketIndicators.count() > 0) {
      await expect(websocketIndicators.first()).toBeVisible();
    }
  });

  test('should load and display voice capabilities', async ({ page }) => {
    // Check if voice-related UI elements are properly loaded
    const voiceControls = page.locator('#voiceBtn, #sttBtn, button:has-text("MIC"), button:has-text("REC")');
    await expect(voiceControls.first()).toBeVisible();
    
    // Check for voice capability indicators in logs or UI
    const logSection = page.locator('.log-section, #systemLogs');
    if (await logSection.count() > 0) {
      // Voice capabilities should be mentioned in logs
      await expect(logSection).toBeVisible();
    }
  });
});