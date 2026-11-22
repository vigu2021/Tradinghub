import AxeBuilder from "@axe-core/playwright";
import { expect, type APIRequestContext, type Page } from "@playwright/test";

/** Where the API runs during a test: the same address the app itself calls. */
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** The signed-in session the setup project saves and signed-in tests start from. */
export const SIGNED_IN = "e2e/.auth/user.json";

export const PASSWORD = "correct horse battery";

/** A fresh address per run, so no test depends on the state of the dev database. */
export function uniqueEmail(label: string): string {
  return `e2e-${label}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

/** A name no other test or run has used, for records in a shared account. */
export function uniqueName(label: string): string {
  return `${label} ${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`;
}

type NewAccount = {
  name: string;
  unit: string;
  type: "cash" | "crypto" | "stock";
  group_name?: string;
};

/**
 * Creates an account straight through the API, for tests about something else. Uses the page's
 * own cookies, so the account belongs to whoever the page is signed in as.
 */
export async function seedAccount(
  request: APIRequestContext,
  account: NewAccount,
): Promise<{ id: number }> {
  const response = await request.post(`${API_URL}/accounts`, {
    data: { group_name: uniqueName("Group"), ...account },
  });
  expect(response.status(), await response.text()).toBe(201);
  return response.json();
}

type NewTransaction = {
  account_id: number;
  amount: string;
  kind: "income" | "expense";
  category: string;
  occurred_at: string;
};

/** Records a transaction straight through the API, as `seedAccount` does an account. */
export async function seedTransaction(
  request: APIRequestContext,
  transaction: NewTransaction,
): Promise<void> {
  const response = await request.post(`${API_URL}/transactions`, {
    data: transaction,
  });
  expect(response.status(), await response.text()).toBe(201);
}

/**
 * Fails with every WCAG 2.2 A and AA violation axe finds on the page as it stands. Motion is
 * switched off first: mid-fade text would be measured at the wrong contrast.
 */
export async function expectAccessible(page: Page): Promise<void> {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .exclude("nextjs-portal")
    .analyze();

  const violations = results.violations.map(
    (violation) =>
      `${violation.id}: ${violation.help} (${violation.nodes.map((node) => node.target.join(" ")).join(", ")})`,
  );
  expect(violations).toEqual([]);
}
