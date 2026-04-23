import { expect, test } from "@playwright/test";
import { setupApiMocks } from "./helpers/mocks";

test("feedback submits from report tab", async ({ page }) => {
  await setupApiMocks(page);
  await page.goto("/reports/j-test");

  await page.getByRole("button", { name: "feedback" }).click();
  await page.getByPlaceholder("Share what should improve").fill("Looks good");
  await page.getByTestId("feedback-submit").click();
  await expect(page.getByText("Feedback submitted.")).toBeVisible();
});
