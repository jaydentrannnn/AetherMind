import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("advanced options and full research flow", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/");

  await page.getByRole("button", { name: /Advanced options/ }).click();
  await page.getByPlaceholder("nature.com").fill("arxiv.org");
  await page.getByRole("button", { name: "Add" }).click();

  await page.getByTestId("topic-input").fill("Transformer attention mechanisms");
  await page.getByTestId("submit-research").click();
  await expect(page).toHaveURL(/\/reports\/j-test/);
  await expect(page.getByTestId("trace-event").first()).toBeVisible();
});
