import { expect, test } from "@playwright/test";

import {
  SIGNED_IN,
  expectAccessible,
  seedAccount,
  uniqueName,
} from "./support";

/**
 * Signed-in screens. Every test starts from the session the setup project saved, and anything a
 * test is not about is created through the API rather than the UI.
 */
test.use({ storageState: SIGNED_IN });

test.describe("accounts page", () => {
  test("lists an account created elsewhere, with its unit", async ({
    page,
  }) => {
    const name = uniqueName("Binance");
    await seedAccount(page.request, { name, unit: "BTC", type: "crypto" });

    await page.goto("/accounts");

    const row = page.getByRole("row", { name: new RegExp(name) });
    await expect(row).toBeVisible();
    await expect(row).toContainText("BTC");
  });

  test("adding an account with the form puts it in the list", async ({
    page,
  }) => {
    const name = uniqueName("Monzo");
    await page.goto("/accounts");

    await page.getByRole("button", { name: "New account" }).click();
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Unit").fill("GBP");
    await page.getByRole("button", { name: "Add account" }).click();

    await expect(
      page.getByRole("row", { name: new RegExp(name) }),
    ).toBeVisible();
  });

  test("a name already in use is refused with the reason", async ({ page }) => {
    const name = uniqueName("Chase");
    await seedAccount(page.request, { name, unit: "GBP", type: "cash" });
    await page.goto("/accounts");

    await page.getByRole("button", { name: "New account" }).click();
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Unit").fill("GBP");
    await page.getByRole("button", { name: "Add account" }).click();

    await expect(page.locator("form").getByRole("alert")).toContainText(
      "You already have an account with that name.",
    );
  });
});

test.describe("accessibility", () => {
  test("the dashboard has no WCAG A or AA violations", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await expectAccessible(page);
  });

  test("the accounts page, with the form open, has no WCAG A or AA violations", async ({
    page,
  }) => {
    await seedAccount(page.request, {
      name: uniqueName("Vanguard"),
      unit: "GBP",
      type: "stock",
    });
    await page.goto("/accounts");
    await page.getByRole("button", { name: "New account" }).click();
    await expect(page.getByLabel("Name")).toBeVisible();

    await expectAccessible(page);
  });
});

test.describe("on a phone", () => {
  test.beforeEach(({ isMobile }) => {
    test.skip(!isMobile, "needs a touch device profile");
  });

  test("the app fits the screen with sign out beside the logo", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    for (const section of ["Dashboard", "Accounts"]) {
      await page.getByRole("link", { name: section }).tap();
      await expect(page.getByRole("link", { name: section })).toHaveAttribute(
        "aria-current",
        "page",
      );

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      const logo = await page
        .locator("header")
        .getByText("Tradinghub", { exact: true })
        .boundingBox();
      const signOut = await page
        .getByRole("button", { name: "Sign out" })
        .boundingBox();
      const middle = (box: typeof logo) =>
        (box?.y ?? 0) + (box?.height ?? 0) / 2;

      expect(overflow).toBeLessThanOrEqual(0);
      expect(Math.abs(middle(logo) - middle(signOut))).toBeLessThan(8);
    }
  });
});
