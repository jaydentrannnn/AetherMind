import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("citation popover displays source info", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/reports/j-test");

  const chip = page.getByTestId("citation-chip").first();
  await expect(chip).toBeVisible();
  await chip.hover();
  await expect(page.getByText("Paper A")).toBeVisible();
});
