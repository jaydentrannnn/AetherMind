import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("navigation between top routes works", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/");
  await page.getByRole("link", { name: "Memory" }).click();
  await expect(page).toHaveURL(/\/memory/);
  await page.goto("/reports/j-test");
  await expect(page.getByText("Agent Trace")).toBeVisible();
  await page.goBack();
  await expect(page).toHaveURL(/\/memory/);
});
