/**
 * Visual Regression Tests
 */
import { test, expect } from "@playwright/test";

test.describe("Visual Tests", () => {
  test("homepage should match snapshot", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveScreenshot("homepage.png", {
      fullPage: true,
      animations: "disabled",
    });
  });

  test("login page should match snapshot", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("login-page.png", {
      fullPage: true,
      animations: "disabled",
    });
  });

  test("register page should match snapshot", async ({ page }) => {
    await page.goto("/register");
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("register-page.png", {
      fullPage: true,
      animations: "disabled",
    });
  });

  test("dashboard should match snapshot (after login)", async ({ page }) => {
    // Mock successful login
    await page.route("**/api/v1/auth/login", (route) => {
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
    });

    await page.route("**/api/v1/auth/me", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          user_id: "123",
          email: "demo@example.com",
          full_name: "Demo User",
          is_active: true,
        }),
      });
    });

    await page.goto("/login");
    await page.fill('input[type="email"]', "demo@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');

    await page.waitForURL(/.*dashboard/);
    await page.waitForLoadState("networkidle");

    await expect(page).toHaveScreenshot("dashboard.png", {
      fullPage: true,
      animations: "disabled",
    });
  });
});
