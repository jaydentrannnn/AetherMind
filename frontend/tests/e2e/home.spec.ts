import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("home renders and theme toggles", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/");

  await expect(page.getByTestId("topic-input")).toBeVisible();
  await expect(page.getByText("What would you like to research?")).toBeVisible();
  await expect(page.getByTestId("submit-research")).toBeDisabled();

  await page.getByTestId("theme-toggle").click();
});

test("submits research and navigates to report", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/");

  await page.getByTestId("topic-input").fill("Transformer attention mechanisms");
  await page.getByTestId("submit-research").click();

  await expect(page).toHaveURL(/\/reports\/j-test/);
});
