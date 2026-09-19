import { expect, Page } from "@playwright/test";

export async function signIn(page: Page, label: string) {
  await page.goto("/");
  await page.getByTestId("dev-signin").selectOption({ label });
  await expect(page.getByTestId("signed-in")).toBeVisible();
}
