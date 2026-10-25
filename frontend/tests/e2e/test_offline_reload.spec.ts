import { test, expect } from "@playwright/test";

test.describe("Offline-first officer PWA (step 43)", () => {
  test("orders page reloads offline after the service worker has cached it", async ({ page, context }) => {
    await page.goto("/orders");
    // the shell is cached during install, so wait until the worker is active and controls the page
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
      if (!navigator.serviceWorker.controller) {
        await new Promise((r) => navigator.serviceWorker.addEventListener("controllerchange", r));
      }
    });

    await context.setOffline(true);
    await page.reload();

    // offline reload must not show the browser's own error page --
    // the cached shell should still render the page structure
    await expect(page.locator("body")).not.toContainText("ERR_INTERNET_DISCONNECTED");
    await context.setOffline(false);
  });
});
