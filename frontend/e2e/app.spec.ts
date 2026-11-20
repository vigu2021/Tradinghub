import { expect, test } from "@playwright/test";

import {
  SIGNED_IN,
  expectAccessible,
  seedAccount,
  seedTransaction,
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

  test("adding an account lands on its new page", async ({ page }) => {
    const name = uniqueName("Monzo");
    await page.goto("/accounts");

    await page.getByRole("link", { name: "New account" }).click();
    await expect(page).toHaveURL(/\/accounts\/new$/);
    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Unit").fill("GBP");
    await page.getByRole("button", { name: "Add account" }).click();

    await expect(page).toHaveURL(/\/accounts\/\d+$/);
    await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
  });

  test("cancelling a new account goes back to the list", async ({ page }) => {
    await page.goto("/accounts/new");

    await page.getByRole("button", { name: "Cancel" }).click();

    await expect(page).toHaveURL(/\/accounts$/);
  });

  test("a name already in use is refused with the reason", async ({ page }) => {
    const name = uniqueName("Chase");
    await seedAccount(page.request, { name, unit: "GBP", type: "cash" });
    await page.goto("/accounts/new");

    await page.getByLabel("Name").fill(name);
    await page.getByLabel("Unit").fill("GBP");
    await page.getByRole("button", { name: "Add account" }).click();

    await expect(page.locator("form").getByRole("alert")).toContainText(
      "You already have an account with that name.",
    );
  });
});

test.describe("an account's own page", () => {
  test("opens from its row in the list", async ({ page }) => {
    const name = uniqueName("Monzo");
    await seedAccount(page.request, { name, unit: "GBP", type: "cash" });
    await page.goto("/accounts");

    await page.getByRole("link", { name }).click();

    await expect(page).toHaveURL(/\/accounts\/\d+$/);
    await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();
    const section = page
      .getByRole("navigation")
      .getByRole("link", { name: "Accounts" });
    await expect(section).toHaveAttribute("aria-current", "true");
    await expect(section).toHaveCSS("font-weight", "600");
  });

  test("lists the account's recent transactions", async ({ page }) => {
    const account = await seedAccount(page.request, {
      name: uniqueName("Monzo"),
      unit: "GBP",
      type: "cash",
    });
    await seedTransaction(page.request, {
      account_id: account.id,
      amount: "2400",
      kind: "income",
      category: "salary",
      occurred_at: "2026-11-12T09:00:00Z",
    });

    await page.goto(`/accounts/${account.id}`);

    const row = page.getByRole("row", { name: /salary/i });
    await expect(row).toContainText("12 Nov");
    await expect(row).toContainText("2400 GBP");
  });

  test("editing its details renames it", async ({ page }) => {
    const account = await seedAccount(page.request, {
      name: uniqueName("Monzo"),
      unit: "GBP",
      type: "cash",
    });
    const renamed = uniqueName("Monzo joint");
    await page.goto(`/accounts/${account.id}`);

    await page.getByRole("button", { name: "Edit", exact: true }).click();
    await page.getByLabel("Name").fill(renamed);
    await page.getByRole("button", { name: "Save" }).click();

    await expect(
      page.getByRole("heading", { name: renamed, level: 1 }),
    ).toBeVisible();
    await expect(page.getByLabel("Name")).toBeHidden();
  });

  test("changing the unit of a non-zero balance says nothing is converted", async ({
    page,
  }) => {
    const account = await seedAccount(page.request, {
      name: uniqueName("Revolut"),
      unit: "GBP",
      type: "cash",
    });
    await seedTransaction(page.request, {
      account_id: account.id,
      amount: "100",
      kind: "income",
      category: "salary",
      occurred_at: "2026-11-12T09:00:00Z",
    });
    await page.goto(`/accounts/${account.id}`);
    await page.getByRole("button", { name: "Edit", exact: true }).click();

    await page.getByLabel("Unit").fill("usd");

    await expect(page.getByLabel("Unit")).toHaveAccessibleDescription(
      "Nothing is converted: 100 GBP becomes 100 USD.",
    );
  });

  test("archiving hides it from the list and restoring brings it back", async ({
    page,
  }) => {
    const name = uniqueName("Old savings");
    const account = await seedAccount(page.request, {
      name,
      unit: "GBP",
      type: "cash",
    });
    await page.goto(`/accounts/${account.id}`);

    await page.getByRole("button", { name: "Archive", exact: true }).click();
    await expect(
      page.getByText("Hidden from your list. Its history is kept."),
    ).toBeVisible();

    await page.getByRole("link", { name: "‹ Accounts" }).click();
    await expect(page.getByRole("link", { name })).toBeHidden();
    await page.getByRole("button", { name: /^Archived \(\d+\)$/ }).click();
    await page.getByRole("link", { name }).click();

    await page.getByRole("button", { name: "Restore" }).click();
    await expect(
      page.getByRole("button", { name: "Archive", exact: true }),
    ).toBeVisible();
  });

  test("an address that is not one of your accounts says so", async ({
    page,
  }) => {
    await page.goto("/accounts/999999999");

    await expect(
      page.getByRole("heading", { name: "No account here" }),
    ).toBeVisible();
  });
});

test.describe("accessibility", () => {
  test("the dashboard has no WCAG A or AA violations", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    await expectAccessible(page);
  });

  test("the accounts list has no WCAG A or AA violations", async ({ page }) => {
    const name = uniqueName("Vanguard");
    await seedAccount(page.request, { name, unit: "GBP", type: "stock" });
    await page.goto("/accounts");
    await expect(page.getByRole("link", { name })).toBeVisible();

    await expectAccessible(page);
  });

  test("the new account page has no WCAG A or AA violations", async ({
    page,
  }) => {
    await page.goto("/accounts/new");
    await expect(page.getByLabel("Name")).toBeVisible();

    await expectAccessible(page);
  });

  test("an account's page has no WCAG A or AA violations", async ({ page }) => {
    const name = uniqueName("Vanguard");
    const account = await seedAccount(page.request, {
      name,
      unit: "GBP",
      type: "stock",
    });
    await page.goto(`/accounts/${account.id}`);
    await expect(page.getByRole("heading", { name, level: 1 })).toBeVisible();

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
    await seedAccount(page.request, {
      name: uniqueName("Vanguard ISA"),
      unit: "GBP",
      type: "stock",
    });
    await page.goto("/dashboard");

    for (const section of ["Dashboard", "Accounts"]) {
      await page.getByRole("link", { name: section }).tap();
      await expect(page.getByRole("link", { name: section })).toHaveAttribute(
        "aria-current",
        "page",
      );

      const overflow = await page.evaluate(
        () =>
          document.documentElement.scrollWidth -
          document.documentElement.clientWidth,
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
