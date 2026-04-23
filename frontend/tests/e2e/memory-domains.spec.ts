import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("memory domain list shows chips", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/memory");

  await page.getByTestId("domain-list-add").fill("example.org");
  await page.getByTestId("domain-list-add").blur();
  await expect(page.getByTestId("domain-chip").first()).toBeVisible();
});
