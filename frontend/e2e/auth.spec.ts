import { expect, test } from "@playwright/test";

import { BASE_URL } from "../playwright.config";

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

test("the dashboard is closed to a visitor without a session", async ({
  page,
}) => {
  await page.goto("/dashboard");

  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign out" })).toHaveCount(0);
});

test("the sign-in screen moves a signed-in visitor along", async ({ page }) => {
  await register(page, uniqueEmail("bounce"));
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.goto("/login");

  await expect(page).toHaveURL(/\/dashboard$/);
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

test("two tabs whose access token expires together both stay signed in", async ({
  page,
  context,
}) => {
  const email = uniqueEmail("tabs");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);
  const secondTab = await context.newPage();
  await secondTab.goto("/dashboard");
  await expect(secondTab.getByRole("heading", { name: email })).toBeVisible();

  const surviving = (await context.cookies()).filter(
    (cookie) => cookie.name !== "access_token",
  );
  await context.clearCookies();
  await context.addCookies(surviving);

  // Hold the first refresh until a second arrives, so an unserialised pair leaves together.
  let refreshesSeen = 0;
  let releaseFirst = () => {};
  const secondArrived = new Promise<void>((resolve) => {
    releaseFirst = resolve;
  });
  await context.route("**/auth/refresh", async (route) => {
    refreshesSeen += 1;
    if (refreshesSeen === 1) {
      await Promise.race([
        secondArrived,
        new Promise((resolve) => setTimeout(resolve, 1000)),
      ]);
    } else {
      releaseFirst();
    }
    await route.continue();
  });
  const refreshStatuses: number[] = [];
  context.on("response", (response) => {
    if (response.url().includes("/auth/refresh")) {
      refreshStatuses.push(response.status());
    }
  });

  await Promise.all([page.reload(), secondTab.reload()]);

  await expect(page.getByRole("heading", { name: email })).toBeVisible();
  await expect(secondTab.getByRole("heading", { name: email })).toBeVisible();
  expect(refreshStatuses.every((status) => status === 204)).toBe(true);
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

test("the right password signs a returning account back in", async ({
  page,
}) => {
  const email = uniqueEmail("signin");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", { name: email })).toBeVisible();
});

test("a wrong password is refused without saying which field was wrong", async ({
  page,
}) => {
  const email = uniqueEmail("wrongpass");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.context().clearCookies();
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
  const registerRequests: string[] = [];
  page.on("request", (request) => {
    if (
      request.method() === "POST" &&
      request.url().includes("/auth/register")
    ) {
      registerRequests.push(request.url());
    }
  });

  await page.goto("/register");
  await page.getByLabel("Email").fill(uniqueEmail("short"));
  await page.getByLabel("Password").fill("short");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(formAlert(page)).toContainText("at least 8 characters");
  await expect(page).toHaveURL(/\/register$/);
  expect(registerRequests).toEqual([]);
});

test("signing out clears the session", async ({ page, context }) => {
  const email = uniqueEmail("signout");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.getByRole("button", { name: "Sign out" }).click();

  await expect
    .poll(async () =>
      (await context.cookies()).some(
        (cookie) => cookie.name === "refresh_token",
      ),
    )
    .toBe(false);
  await expect(page).toHaveURL(/\/login$/);

  await page.goto("/dashboard");

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: email })).toHaveCount(0);
});

test("a lost connection offers a retry instead of signing the visitor out", async ({
  page,
}) => {
  const email = uniqueEmail("offline");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.route("**/auth/me", (route) => route.abort());
  await page.reload();

  await expect(page).toHaveURL(/\/dashboard$/);
  // Two network retries with backoff run before the query gives up.
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible({
    timeout: 15_000,
  });

  await page.unroute("**/auth/me");
  await page.getByRole("button", { name: "Try again" }).click();

  await expect(page.getByRole("heading", { name: email })).toBeVisible();
});

test("a failing server offers a retry instead of signing the visitor out", async ({
  page,
}) => {
  const email = uniqueEmail("servererror");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  await page.route("**/auth/me", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      headers: {
        "access-control-allow-origin": BASE_URL,
        "access-control-allow-credentials": "true",
      },
      body: JSON.stringify({
        error: { code: "internal_error", message: "Internal error." },
      }),
    }),
  );
  await page.reload();

  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("a refresh that never arrives offers a retry instead of signing the visitor out", async ({
  page,
  context,
}) => {
  const email = uniqueEmail("refreshlost");
  await register(page, email);
  await expect(page).toHaveURL(/\/dashboard$/);

  const surviving = (await context.cookies()).filter(
    (cookie) => cookie.name !== "access_token",
  );
  await context.clearCookies();
  await context.addCookies(surviving);
  await page.route("**/auth/refresh", (route) => route.abort());
  await page.reload();

  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page).toHaveURL(/\/dashboard$/);
});

test("a session that dies while the dashboard is open ends at the login screen", async ({
  page,
  context,
}) => {
  await page.clock.install();
  await register(page, uniqueEmail("revoked"));
  await expect(page).toHaveURL(/\/dashboard$/);

  await context.clearCookies();
  await page.clock.fastForward("03:00");
  // React Query listens for this on window, and a plain Event does not bubble there from document.
  await page.evaluate(() =>
    window.dispatchEvent(new Event("visibilitychange")),
  );

  await expect(page).toHaveURL(/\/login$/);
  await page.waitForTimeout(1500);
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("a rate limited login says when to try again and holds the button", async ({
  page,
}) => {
  await page.route("**/auth/login", (route) =>
    route.fulfill({
      status: 429,
      headers: {
        "content-type": "application/json",
        "retry-after": "900",
        "access-control-allow-origin": BASE_URL,
        "access-control-allow-credentials": "true",
        "access-control-expose-headers": "Retry-After",
      },
      body: JSON.stringify({
        error: {
          code: "rate_limited",
          message: "Too many attempts. Please try again later.",
        },
      }),
    }),
  );

  await page.goto("/login");
  await page.getByLabel("Email").fill(uniqueEmail("locked"));
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(formAlert(page)).toContainText("Try again in 15 minutes");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeDisabled();
});
