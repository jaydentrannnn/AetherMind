import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("memory semantic search returns mocked result", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/memory");

  await page.getByTestId("memory-search-input").fill("attention");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByTestId("memory-search-result").first()).toContainText("Attention report");
});
