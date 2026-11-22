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
    await page.getByRole("combobox", { name: "Group" }).fill("Banks");
    await page.keyboard.press("Tab");
    await page.getByRole("combobox", { name: "Unit" }).fill("GBP");
    await page.keyboard.press("Tab");
    await page.getByLabel("Type").selectOption("cash");
    await page.getByLabel("Name").fill(name);
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

    await page.getByRole("combobox", { name: "Group" }).fill("E2E");
    await page.keyboard.press("Tab");
    await page.getByRole("combobox", { name: "Unit" }).fill("GBP");
    await page.keyboard.press("Tab");
    await page.getByLabel("Type").selectOption("cash");
    await page.getByLabel("Name").fill(name);
    await page.getByRole("button", { name: "Add account" }).click();

    await expect(page.locator("form").getByRole("alert")).toContainText(
      "You already have an account with that name.",
    );
  });
});

test.describe("the new account form", () => {
  test("the group box offers your groups, and creating a new one", async ({
    page,
  }) => {
    const existing = uniqueName("Savings");
    await seedAccount(page.request, {
      name: uniqueName("ISA"),
      unit: "GBP",
      type: "stock",
      group_name: existing,
    });
    await page.goto("/accounts/new");
    const group = page.getByRole("combobox", { name: "Group" });
    const options = page.getByRole("listbox").getByRole("option");

    await group.click();
    await expect(options.filter({ hasText: existing })).toBeVisible();

    await group.fill("Home safe");
    await expect(
      options.filter({ hasText: '+ Create "Home safe"' }),
    ).toBeVisible();
  });

  test("a group typed in another case files under the existing one", async ({
    page,
  }) => {
    const existing = uniqueName("Binance");
    await seedAccount(page.request, {
      name: uniqueName("Binance BTC"),
      unit: "BTC",
      type: "crypto",
      group_name: existing,
    });
    await page.goto("/accounts/new");
    const group = page.getByRole("combobox", { name: "Group" });

    await group.fill(existing.toLowerCase());
    await page.keyboard.press("Tab");
    await page.keyboard.press("Escape");

    await expect(group).toHaveValue(existing);
  });

  test("the name fills itself until you type your own", async ({ page }) => {
    await page.goto("/accounts/new");
    const group = page.getByRole("combobox", { name: "Group" });
    const name = page.getByLabel("Name");

    await group.fill("Revolut");
    await page.keyboard.press("Tab");
    await page.getByRole("combobox", { name: "Unit" }).fill("eur");
    await page.keyboard.press("Tab");
    await expect(name).toHaveValue("Revolut EUR");

    await name.fill("Holiday money");
    await group.fill("Monzo");
    await page.keyboard.press("Tab");
    await expect(name).toHaveValue("Holiday money");
  });

  test("submitting with nothing filled in moves to the first field", async ({
    page,
  }) => {
    await page.goto("/accounts/new");

    await page.locator("button[type=submit]").click();

    await expect(page.getByRole("combobox", { name: "Group" })).toBeFocused();
  });

  test("the type has to be picked", async ({ page }) => {
    await page.goto("/accounts/new");

    await page
      .getByRole("combobox", { name: "Group" })
      .fill(uniqueName("Cash"));
    await page.keyboard.press("Tab");
    await page.getByRole("combobox", { name: "Unit" }).fill("GBP");
    await page.keyboard.press("Tab");
    await page.locator("button[type=submit]").click();

    await expect(page.getByText("Say what it is.")).toBeVisible();
    await expect(page.getByLabel("Type")).toBeFocused();
  });
});

test.describe("groups in the accounts list", () => {
  test("a small group starts open", async ({ page }) => {
    const group = uniqueName("Banks");
    const name = uniqueName("Monzo");
    await seedAccount(page.request, {
      name,
      unit: "GBP",
      type: "cash",
      group_name: group,
    });
    await page.goto("/accounts");

    await expect(page.getByRole("button", { name: group })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    await expect(page.getByRole("link", { name })).toBeVisible();
  });

  test("a group of more than five starts closed and opens when clicked", async ({
    page,
  }) => {
    const group = uniqueName("Exchange");
    for (const unit of ["BTC", "ETH", "USDT", "SOL", "BNB", "ADA"]) {
      await seedAccount(page.request, {
        name: `${group} ${unit}`,
        unit,
        type: "crypto",
        group_name: group,
      });
    }
    await page.goto("/accounts");
    const heading = page.getByRole("button", { name: group });
    const btc = page.getByRole("link", { name: `${group} BTC` });

    await expect(heading).toHaveAttribute("aria-expanded", "false");
    await expect(btc).toBeHidden();

    await heading.click();

    await expect(heading).toHaveAttribute("aria-expanded", "true");
    await expect(btc).toBeVisible();
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

    await page.getByRole("combobox", { name: "Unit" }).fill("usd");

    await expect(
      page.getByRole("combobox", { name: "Unit" }),
    ).toHaveAccessibleDescription(
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
