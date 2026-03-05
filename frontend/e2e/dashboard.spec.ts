/**
 * Dashboard E2E Tests
 */
import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', "demo@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.click('button[type="submit"]');
    await page.waitForURL(/.*dashboard/);
  });

  test("should display dashboard", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Welcome to Image Rating");
  });

  test("should display stats cards", async ({ page }) => {
    // Check for stat cards
    const statCards = page.locator(".grid").filter({ hasText: /Total Images|Your Ratings|Average Rating/ });
    await expect(statCards.first()).toBeVisible();
  });

  test("should navigate using nav menu", async ({ page }) => {
    // Click Dashboard link
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(/\/dashboard$/);

    // Click Images link (may not exist yet)
    const imagesLink = page.locator('text=Images');
    if (await imagesLink.isVisible()) {
      await imagesLink.click();
    }
  });

  test("should have working action buttons", async ({ page }) => {
    // Upload button
    const uploadButton = page.locator('text=Upload New Image');
    await expect(uploadButton).toBeVisible();

    // Browse button
    const browseButton = page.locator('text=Browse Gallery');
    await expect(browseButton).toBeVisible();
  });
});
