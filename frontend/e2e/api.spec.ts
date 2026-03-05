/**
 * API Integration Tests (with mocked backend)
 */
import { test, expect } from "@playwright/test";

test.describe("API Integration", () => {
  test("should handle API errors gracefully", async ({ page }) => {
    // Intercept API calls and mock failures
    await page.route("**/api/v1/auth/login", (route) => {
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    await page.goto("/login");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password");
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator("text=Internal server error").or(page.locator(".destructive"))).toBeVisible({ timeout: 5000 });
  });

  test("should handle network timeout", async ({ page }) => {
    // Mock network delay
    await page.route("**/api/v1/auth/login", (route) => {
      setTimeout(() => {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            access_token: "mock_token",
            refresh_token: "mock_refresh",
            token_type: "bearer",
            expires_in: 1800,
          }),
        });
      }, 100);
    });

    await page.goto("/login");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password");
    await page.click('button[type="submit"]');

    // Button should show loading state
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toContainText("Signing in...", { timeout: 100 });
  });
});
