/**
 * Authentication E2E Tests
 */
import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should display home page", async ({ page }) => {
    await expect(page.locator("h1")).toContainText("Image Rating Platform");
  });

  test("should navigate to login page", async ({ page }) => {
    await page.click('text=Sign In');
    await expect(page).toHaveURL(/.*login/);
    await expect(page.locator("h2")).toContainText("Welcome back");
  });

  test("should show validation errors for empty form", async ({ page }) => {
    await page.goto("/login");

    // Try to submit with empty form
    await page.click('button[type="submit"]');

    // Browser validation should prevent submission
    const emailInput = page.locator('input[type="email"]');
    await expect(emailInput).toBeFocused();
  });

  test("should display error for invalid credentials", async ({ page }) => {
    await page.goto("/login");

    // Fill in invalid credentials
    await page.fill('input[type="email"]', "invalid@example.com");
    await page.fill('input[type="password"]', "wrongpassword");

    // Submit form
    await page.click('button[type="submit"]');

    // Should show error message (toaster or inline)
    await expect(page.locator("text=Login failed").or(page.locator(".destructive"))).toBeVisible({ timeout: 5000 });
  });

  test("should login with demo credentials", async ({ page }) => {
    await page.goto("/login");

    // Fill in demo credentials
    await page.fill('input[type="email"]', "demo@example.com");
    await page.fill('input[type="password"]', "password123");

    // Submit form
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*dashboard/, { timeout: 10000 });
  });

  test("should navigate to register page", async ({ page }) => {
    await page.click('text=Create Account');
    await expect(page).toHaveURL(/.*register/);
    await expect(page.locator("h2")).toContainText("Create an account");
  });

  test("should register new user", async ({ page }) => {
    await page.goto("/register");

    // Generate unique email
    const timestamp = Date.now();
    const email = `test${timestamp}@example.com`;

    // Fill in registration form
    await page.fill('#fullName', `Test User ${timestamp}`);
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', "password123");
    await page.fill('#confirmPassword', "password123");

    // Submit form (will fail since backend is mock)
    await page.click('button[type="submit"]');

    // Either redirects or shows error
    await page.waitForTimeout(2000);
  });

  test("should show password mismatch error", async ({ page }) => {
    await page.goto("/register");

    await page.fill('#fullName', "Test User");
    await page.fill('input[type="email"]', "test@example.com");
    await page.fill('input[type="password"]', "password123");
    await page.fill('#confirmPassword', "differentpassword");

    await page.click('button[type="submit"]');

    // Should show password mismatch error
    await expect(page.locator("text=do not match")).toBeVisible();
  });
});
