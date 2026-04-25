import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("citation popover displays source info", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/reports/j-test");

  const chip = page.getByTestId("citation-chip").first();
  await expect(chip).toBeVisible();
  await expect(chip).toContainText("[1]");
  await expect(chip).toHaveAttribute("href", "https://arxiv.org/abs/1234.5678");
  await chip.hover();
  await expect(page.getByText("Paper A")).toBeVisible();

  await page.getByRole("button", { name: "sources" }).click();
  const sourceLink = page.getByTestId("source-link").first();
  await expect(sourceLink).toContainText("Paper A");
  await expect(sourceLink).toHaveAttribute("href", "https://arxiv.org/abs/1234.5678");
});
