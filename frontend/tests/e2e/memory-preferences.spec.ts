import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("memory preferences can be edited and saved", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/memory");

  await expect(page.getByTestId("preference-row").first()).toBeVisible();
  await page.locator("[data-testid='preference-row'] input").nth(1).fill("detailed");
  await page.getByTestId("preference-save").click();
});
