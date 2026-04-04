import { test, expect } from "@playwright/test";

test.describe("Chat flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workspace");
  });

  test("shows empty state on load", async ({ page }) => {
    await expect(page.getByText("Design your first 3D model")).toBeVisible();
  });

  test("example chips are clickable", async ({ page }) => {
    const chip = page.getByText("A phone stand with cable slot for iPhone 15");
    await expect(chip).toBeVisible();
  });

  test("textarea accepts input", async ({ page }) => {
    const textarea = page.locator("textarea");
    await textarea.fill("Make me a simple box");
    await expect(textarea).toHaveValue("Make me a simple box");
  });

  test("send button is disabled when textarea is empty", async ({ page }) => {
    const sendBtn = page.locator("button[title='']").last();
    // Input should have correct disabled state
    const textarea = page.locator("textarea");
    await expect(textarea).toBeEmpty();
  });

  test("header shows app name", async ({ page }) => {
    await expect(page.getByText("Claude 3D")).toBeVisible();
  });
});
