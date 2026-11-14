import { expect, type Locator, type Page, test } from "@playwright/test";

import { expectAccessible } from "./support";

/**
 * The public entry: the landing page and the two auth screens. Behaviour first, then layout at
 * three widths, then pixel snapshots that catch visual drift no assertion names.
 */

const VIEWPORTS = {
  phone: { width: 390, height: 844 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1280, height: 800 },
} as const;

const ENTRY_PAGES = [
  { path: "/", name: "landing" },
  { path: "/login", name: "login" },
  { path: "/register", name: "register" },
] as const;

/** Next's dev-only badge sits in a corner of every page and would make each snapshot flaky. */
const HIDE_DEV_OVERLAY = "e2e/hide-dev-overlay.css";

/** The whole logo: the candle mark and the wordmark side by side, in the page header. */
function logo(page: Page) {
  return page
    .locator("header")
    .getByText("Tradinghub", { exact: true })
    .locator("..");
}

async function sizeOf(locator: Locator): Promise<string> {
  const box = await locator.boundingBox();
  return `${Math.round(box?.width ?? 0)}x${Math.round(box?.height ?? 0)}`;
}

/** An anonymous visitor's session probe is refused by design; nothing else may be. */
const EXPECTED_REFUSALS = [/\/auth\/me$/, /\/auth\/refresh$/];

/**
 * What went wrong while the test ran: uncaught exceptions, console errors, failed requests, and
 * any 4xx or 5xx response other than the expected session-probe 401s. The browser logs each of
 * those 401s as "Failed to load resource"; responses are checked directly instead, so that line
 * is skipped rather than hiding a real 404.
 */
function collectProblems(page: Page): string[] {
  const problems: string[] = [];
  page.on("pageerror", (error) => problems.push(error.message));
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      !message.text().startsWith("Failed to load resource")
    ) {
      problems.push(message.text());
    }
  });
  page.on("requestfailed", (request) => {
    const reason = request.failure()?.errorText ?? "";
    // Next prefetches pages as their links appear; navigating cancels the ones still in flight.
    if (reason !== "net::ERR_ABORTED") {
      problems.push(`failed ${request.url()}: ${reason}`);
    }
  });
  page.on("response", (response) => {
    const expected =
      response.status() === 401 &&
      EXPECTED_REFUSALS.some((path) =>
        path.test(new URL(response.url()).pathname),
      );
    if (response.status() >= 400 && !expected) {
      problems.push(`${response.status()} ${response.url()}`);
    }
  });
  return problems;
}

function channels(color: string): number[] {
  return (color.match(/\d+(\.\d+)?/g) ?? []).map(Number);
}

/**
 * WCAG contrast ratio of a computed colour against an opaque background. A translucent colour is
 * blended over the background first, so a transparent border scores 1, not black's 21.
 */
function contrastOver(color: string, background: string): number {
  const [red = 0, green = 0, blue = 0, alpha = 1] = channels(color);
  const [backRed = 0, backGreen = 0, backBlue = 0] = channels(background);
  const blended = [
    red * alpha + backRed * (1 - alpha),
    green * alpha + backGreen * (1 - alpha),
    blue * alpha + backBlue * (1 - alpha),
  ];
  const luminance = ([r = 0, g = 0, b = 0]: number[]) =>
    [r, g, b]
      .map((channel) => {
        const value = channel / 255;
        return value <= 0.03928
          ? value / 12.92
          : ((value + 0.055) / 1.055) ** 2.4;
      })
      .reduce(
        (sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index]!,
        0,
      );
  const [lighter = 0, darker = 0] = [
    luminance(blended),
    luminance([backRed, backGreen, backBlue]),
  ].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

test.describe("landing page", () => {
  test("says what the product is and offers one way in", async ({ page }) => {
    await page.goto("/");

    await expect(
      page.getByRole("heading", {
        level: 1,
        name: "A clearer record of every decision.",
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Start your journal" }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole("region", { name: "What the journal looks like" }),
    ).toBeVisible();
  });

  test("Get started opens registration", async ({ page, isMobile }) => {
    test.skip(isMobile, "the header button is hidden on phones");
    await page.goto("/");

    await page.getByRole("link", { name: "Get started" }).click();

    await expect(page).toHaveURL(/\/register$/);
    await expect(
      page.getByRole("heading", { name: "Create your account" }),
    ).toBeVisible();
  });

  test("on a phone, Start your journal opens registration", async ({
    page,
  }) => {
    await page.setViewportSize(VIEWPORTS.phone);
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Get started" })).toBeHidden();

    await page
      .getByRole("link", { name: "Start your journal" })
      .first()
      .click();

    await expect(page).toHaveURL(/\/register$/);
  });

  test("Sign in opens the login screen", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: "Sign in", exact: true }).click();

    await expect(page).toHaveURL(/\/login$/);
    await expect(
      page.getByRole("heading", { name: "Welcome back." }),
    ).toBeVisible();
  });

  test("its entrance is staggered, header first and the preview last", async ({
    page,
  }) => {
    await page.goto("/");

    const delays = await page
      .locator(".rise")
      .evaluateAll((elements) =>
        elements.map((element) =>
          parseFloat(getComputedStyle(element).animationDelay),
        ),
      );

    expect(delays.length).toBeGreaterThan(1);
    expect(delays).toEqual([...delays].sort((a, b) => a - b));
    expect(new Set(delays).size).toBe(delays.length);
  });

  test("a visitor who asks for reduced motion gets none", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");

    await expect(page.getByRole("heading", { level: 1 })).toHaveCSS(
      "animation-name",
      "none",
    );
  });
});

test.describe("moving between sign in and sign up", () => {
  // Regression: blur validation on the autofocused email used to show an error on mouse down,
  // which pushed the link out from under the pointer and swallowed the click.
  test("pressing Create an account leaves the login form still, so one click lands", async ({
    page,
  }) => {
    // The entrance animation moves the link on its own; switch it off so only layout can.
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/login");
    await expect(page.getByLabel("Email")).toBeFocused();
    const link = page.getByRole("link", { name: "Create an account" });
    const before = await link.boundingBox();

    await link.hover();
    await page.mouse.down();
    await expect(page.locator("form").getByRole("alert")).toHaveCount(0);
    expect(await link.boundingBox()).toEqual(before);
    await page.mouse.up();

    await expect(page).toHaveURL(/\/register$/);
  });

  test("one click on Sign in goes back to the login screen", async ({
    page,
  }) => {
    await page.goto("/register");
    await expect(page.getByLabel("Email")).toBeFocused();

    await page.getByRole("link", { name: "Sign in", exact: true }).click();

    await expect(page).toHaveURL(/\/login$/);
  });

  test("the switch works from the keyboard", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Email")).toBeFocused();

    // Email, then password, then the submit button, then the link.
    for (let step = 0; step < 3; step += 1) {
      await page.keyboard.press("Tab");
    }
    await expect(
      page.getByRole("link", { name: "Create an account" }),
    ).toBeFocused();
    await page.keyboard.press("Enter");

    await expect(page).toHaveURL(/\/register$/);
  });

  test("an empty form is only flagged once it is submitted", async ({
    page,
  }) => {
    await page.goto("/login");
    await page.getByLabel("Email").blur();
    await expect(page.locator("form").getByRole("alert")).toHaveCount(0);

    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.locator("form").getByRole("alert").first()).toBeVisible();
  });

  // Regression: the fields once had no outline at rest, so an empty form showed nothing to type in.
  for (const { path, name } of ENTRY_PAGES.filter(
    (entry) => entry.path !== "/",
  )) {
    test(`the ${name} fields are visible before they are clicked`, async ({
      page,
    }) => {
      await page.goto(path);
      const password = page.getByLabel("Password");
      await expect(password).not.toBeFocused();

      const [border, ground] = await Promise.all([
        password.evaluate((input) => getComputedStyle(input).borderTopColor),
        page.evaluate(() => getComputedStyle(document.body).backgroundColor),
      ]);

      expect(contrastOver(border, ground)).toBeGreaterThanOrEqual(3);
    });
  }

  test("the logo, mark and wordmark, keeps one size across the entry pages", async ({
    page,
  }) => {
    const sizes = new Set<string>();
    for (const { path } of ENTRY_PAGES) {
      await page.goto(path);
      await expect(logo(page)).toBeVisible();
      sizes.add(
        `${await sizeOf(logo(page))} mark ${await sizeOf(logo(page).locator("svg"))}`,
      );
    }

    expect([...sizes]).toHaveLength(1);
  });

  test("nothing fails along the way", async ({ page }) => {
    const problems = collectProblems(page);

    await page.goto("/");
    await page.getByRole("link", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/login$/);
    await page.getByRole("link", { name: "Create an account" }).click();
    await expect(page).toHaveURL(/\/register$/);

    expect(problems).toEqual([]);
  });
});

test.describe("on a touch screen", () => {
  test.beforeEach(({ isMobile }) => {
    test.skip(!isMobile, "needs a touch device profile");
  });

  test("a tap on Start your journal opens registration", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: "Start your journal" }).first().tap();

    await expect(page).toHaveURL(/\/register$/);
  });

  test("a tap on Create an account opens registration", async ({ page }) => {
    await page.goto("/login");

    await page.getByRole("link", { name: "Create an account" }).tap();

    await expect(page).toHaveURL(/\/register$/);
  });

  test("a tap on Sign in goes back to the login screen", async ({ page }) => {
    await page.goto("/register");

    await page.getByRole("link", { name: "Sign in", exact: true }).tap();

    await expect(page).toHaveURL(/\/login$/);
  });
});

test.describe("accessibility", () => {
  for (const { path, name } of ENTRY_PAGES) {
    test(`${name} has no WCAG A or AA violations`, async ({ page }) => {
      await page.goto(path);
      await expect(logo(page)).toBeVisible();

      await expectAccessible(page);
    });
  }
});

test.describe("device basics", () => {
  // iOS zooms the page into any input whose text is smaller than 16px.
  for (const { path, name } of ENTRY_PAGES.filter(
    (entry) => entry.path !== "/",
  )) {
    test(`the ${name} inputs are large enough that a phone does not zoom in`, async ({
      page,
    }) => {
      await page.goto(path);

      for (const input of await page.getByRole("textbox").all()) {
        const size = await input.evaluate((element) =>
          parseFloat(getComputedStyle(element).fontSize),
        );
        expect(size).toBeGreaterThanOrEqual(16);
      }
    });
  }

  // WCAG 2.5.8 exempts a link inside a sentence; every other control needs room for a finger.
  for (const { path, name } of ENTRY_PAGES) {
    test(`every control on ${name} is at least 44px tall`, async ({ page }) => {
      await page.setViewportSize(VIEWPORTS.phone);
      await page.goto(path);
      await expect(logo(page)).toBeVisible();

      const tooSmall = await page.locator("a, button").evaluateAll((controls) =>
        controls
          .filter((control) => {
            const box = control.getBoundingClientRect();
            const inSentence = control.parentElement?.tagName === "P";
            const devToolsOnly = control.hasAttribute("data-next-mark");
            return (
              box.height > 0 &&
              !inSentence &&
              !devToolsOnly &&
              Math.round(box.height) < 44
            );
          })
          .map(
            (control) =>
              `${control.textContent?.trim()} (${control.getBoundingClientRect().height}px)`,
          ),
      );

      expect(tooSmall).toEqual([]);
    });
  }
});

for (const [device, viewport] of Object.entries(VIEWPORTS)) {
  test.describe(`at ${device} width`, () => {
    test.use({ viewport });

    for (const { path, name } of ENTRY_PAGES) {
      test(`${name} fits the screen without sideways scrolling`, async ({
        page,
      }) => {
        await page.goto(path);
        await expect(logo(page)).toBeVisible();

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - window.innerWidth,
        );

        expect(overflow).toBeLessThanOrEqual(0);
      });

      test(`${name} matches its snapshot`, async ({ page }) => {
        await page.goto(path);
        await expect(logo(page)).toBeVisible();

        await expect(page).toHaveScreenshot(`${name}-${device}.png`, {
          fullPage: true,
          animations: "disabled",
          caret: "hide",
          stylePath: HIDE_DEV_OVERLAY,
        });
      });
    }
  });
}
