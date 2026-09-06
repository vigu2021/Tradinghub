import { expect, test } from "@playwright/test";

const PASSWORD = "correct horse battery";

/** A fresh address per run, so the suite never depends on the state of the dev database. */
function uniqueEmail(label: string): string {
  return `e2e-${label}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

/**
 * Next renders its own role="alert" route announcer, so an unscoped getByRole("alert") always
 * matches two elements. The form's own errors are the ones under test.
 */
function formAlert(page: import("@playwright/test").Page) {
  return page.locator("form").getByRole("alert");
}

async function register(page: import("@playwright/test").Page, email: string) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
}

test("the root sends a visitor to the login screen", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
});

test("registering signs the new account in", async ({ page }) => {
  const email = uniqueEmail("signup");

  await register(page, email);

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: email })).toBeVisible();
});

test("the session survives a reload", async ({ page }) => {
  const email = uniqueEmail("reload");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.reload();

  await expect(page.getByRole("heading", { name: email })).toBeVisible();
});

test("both cookies are HttpOnly and the refresh one is scoped to /auth", async ({
  page,
  context,
}) => {
  await register(page, uniqueEmail("cookies"));
  await expect(page).toHaveURL(/\/dashboard$/);

  const cookies = await context.cookies();
  const access = cookies.find((cookie) => cookie.name === "access_token");
  const refresh = cookies.find((cookie) => cookie.name === "refresh_token");

  expect(access?.httpOnly).toBe(true);
  expect(refresh?.httpOnly).toBe(true);
  expect(access?.path).toBe("/");
  expect(refresh?.path).toBe("/auth");
});

test("an expired access token is rotated behind the scenes", async ({
  page,
  context,
}) => {
  const email = uniqueEmail("rotate");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  // Drop only the access token. The refresh cookie survives, so the interceptor should notice the
  // 401, rotate, and replay — the user never sees a login screen.
  const surviving = (await context.cookies()).filter(
    (cookie) => cookie.name !== "access_token",
  );
  await context.clearCookies();
  await context.addCookies(surviving);

  const refreshed = page.waitForResponse(
    (response) =>
      response.url().includes("/auth/refresh") && response.status() === 204,
  );
  await page.reload();

  await refreshed;
  await expect(page.getByRole("heading", { name: email })).toBeVisible();
});

test("a duplicate email is rejected with a way out", async ({ page }) => {
  const email = uniqueEmail("duplicate");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  // A signed-in visitor is bounced off /register, so the second attempt has to be a new one.
  await page.context().clearCookies();
  await register(page, email);

  await expect(formAlert(page)).toContainText("already registered");
  await page.getByRole("link", { name: "Sign in instead" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("a wrong password is refused without saying which field was wrong", async ({
  page,
}) => {
  const email = uniqueEmail("wrongpass");
  await register(page, email);

  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("not the password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(formAlert(page)).toHaveText("Email or password is incorrect.");
  await expect(page).toHaveURL(/\/login$/);
});

test("an unknown email is refused identically", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(uniqueEmail("nobody"));
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(formAlert(page)).toHaveText("Email or password is incorrect.");
});

test("the form rejects a short password before reaching the server", async ({
  page,
}) => {
  await page.goto("/register");
  await page.getByLabel("Email").fill(uniqueEmail("short"));
  await page.getByLabel("Password").fill("short");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(formAlert(page)).toContainText("at least 8 characters");
  await expect(page).toHaveURL(/\/register$/);
});

test("signing out clears the session", async ({ page, context }) => {
  await register(page, uniqueEmail("signout"));
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.getByRole("button", { name: "Sign out" }).click();

  await expect
    .poll(async () =>
      (await context.cookies()).some(
        (cookie) => cookie.name === "refresh_token",
      ),
    )
    .toBe(false);
});
