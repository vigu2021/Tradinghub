# Design

How Tradinghub looks, behaves, and is checked in a browser. Code conventions live in the repo's
`CONVENTIONS.md`; this file is the visual and interaction half.

## Theme: Statement Swiss

Light, typeset, square-cornered: a well-set financial statement. Tokens live in
`src/app/globals.css`; never hard-code a colour.

| Token                         | Use                                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------------------- |
| `ground`                      | page background                                                                              |
| `surface`                     | tinted groups: alternating table rows, filled inputs, call-to-action bands                   |
| `ink`, `ink-dim`, `ink-faint` | primary text, secondary text, captions and units; each keeps 4.5:1 on `ground` and `surface` |
| `rule`, `rule-strong`         | a divider, only when spacing alone is ambiguous                                              |
| `control`                     | the outline of an input at rest: the lightest grey that keeps 3:1 against `ground`           |
| `accent` + `accent-ink`       | the primary action and the current nav link, nothing else                                    |
| `positive`, `negative`        | gain and loss only, never decoration                                                         |
| `danger`                      | errors                                                                                       |

Type: **Archivo** for everything (`font-sans`, `font-display`), **IBM Plex Mono** only for numbers
(`font-mono`).

## Rules

- **Hierarchy comes from size, weight and space, not lines.** No borders between rows or around
  sections. Group with spacing and the `surface` tint.
- **Numbers are the hero.** Amounts use `font-mono tabular-nums`, right aligned, with the unit after
  them in `ink-faint`. Show the string the API sent; never reformat money in the browser.
- **One accent, for actions.** One primary button per view. Everything else is a ghost button or a
  link.
- **Labels:** small uppercase captions (`text-xs font-medium uppercase tracking-[0.12em]
text-ink-faint`) above figures and table columns; sentence case everywhere else.
- **Inputs are visible before they are touched:** a 1px `control` outline at rest, `accent` on
  focus, `danger` on error. WCAG asks 3:1 for a control's boundary; a fill-only field fails it.
- **One logo size** everywhere, so moving between pages never makes it jump.
- **Avoid:** gradients, glass effects, coloured left-border cards, cards inside cards, rounded
  corners, decorative lines or grids, emoji, more than one accent.

## Interaction

- **Forms validate on submit, then on every change** (`mode: "onSubmit"`, `reValidateMode:
"onChange"`). Validating on blur flags an empty field the moment someone clicks a link, and the
  error shifting the layout swallows that click.
- **Errors stay inline.** A field error sits under its field; a request error is an `ErrorBanner`
  above the submit button. No toasts for failures.
- **A pending action says so** on its button ("Adding", "Signing in") and disables it.
- **No layout shift on interaction.** Anything that appears on focus, hover or mouse down must not
  move what the pointer is on.
- **Entrance motion:** the `rise` class with a growing `[animation-delay:…ms]` per element, once
  per page load, on the shell rather than per page inside the app. `prefers-reduced-motion` turns
  it off. Never use the `animation` shorthand on `.rise`; it resets the delay.
- **An empty state says what is missing, what it is for, and how to add one.** Never just "nothing
  here".
- **Loading:** a static page (the landing page) loads nothing. An app page shows a short text or
  skeleton only on its first load; later fetches keep the previous data on screen.

## Phones and touch

- **Mobile first, then widen.** Unprefixed classes are the phone layout; `sm:` and `md:` add the
  wider one. Nothing may scroll sideways at 390px.
- **Inputs are at least 16px text** (`text-base`). iOS zooms the page into any smaller input.
- **Touch targets are at least 44px tall** (`min-h-11`): buttons, nav links, standalone links. A
  link inside a sentence is exempt (WCAG 2.5.8).
- **Every control has a pressed state** (`active:`), since the default tap flash is turned off.
- **Nothing depends on hover.** Hover may decorate; it never reveals a control or information.
- **Headers fold to two rows on a phone:** the logo and the main action on top, navigation as a full
  row below (`order-last w-full sm:order-none sm:w-auto`).
- **Page titles step down on phones** (`text-[2rem] sm:text-[2.5rem]`), and long values such as an
  email use `break-words`.
- **Use `dvh`, not `vh`,** for full-height layouts, so the mobile browser bar does not cut them off.

## Checking it in a browser

End-to-end tests are Playwright, in `e2e/`. The API must be running (`make api`); Playwright starts
the web server itself or reuses the one on port 3210.

- **Locate by role and label** (`getByRole`, `getByLabel`), never by CSS class or test id when a
  role exists. Use auto-waiting assertions (`await expect(locator).toBeVisible()`), never
  `waitForTimeout`.
- **One behaviour per test**, named as a sentence about that behaviour. A bug fix gets a regression
  test that fails without the fix.
- **Tests run in parallel, in any order** (`fullyParallel`, 10 workers). A test never relies on
  another having run, and names what it creates with `uniqueName`. `npm run e2e:quick` runs desktop
  only while working; `npm run e2e` runs both devices before a commit.
- **Sign in once.** The `setup` project registers one user through the API and saves its cookies to
  `e2e/.auth/user.json` (gitignored); signed-in specs start from it with
  `test.use({ storageState: SIGNED_IN })`. Only `auth.spec.ts`, which tests signing in itself, goes
  through the form.
- **Create what a test is not about through the API** (`seedAccount` in `e2e/support.ts`), and use
  the UI only for the behaviour under test. Give shared records unique names (`uniqueName`).
- **Every page gets an accessibility scan** (`expectAccessible`): axe with WCAG 2.2 A and AA, motion
  off so faded text is not measured mid-animation. A new page adds one.
- **Layout is checked at three widths**: phone 390, tablet 768, desktop 1280. Each public page must
  not scroll sideways at any of them.
- **A real phone profile runs too** (`mobile-chrome`, a Pixel 7: touch, a 2.6x screen, a mobile user
  agent). Touch tests use `tap()` and skip on desktop with `test.skip(!isMobile)`. An iPhone
  profile (WebKit) needs its system libraries first: `sudo npx playwright install-deps webkit`.
- **Measure sizes in whole pixels** (`Math.round`): a moving element reports 43.999996px.
- **Measure sideways overflow against `clientWidth`, never `innerWidth`.** A phone widens
  `innerWidth` to fit content that is too wide, so the overflow always reads 0. Give the page real
  data first: an empty table never overflows.
- **Visual snapshots** (`toHaveScreenshot`) cover the public pages at each width, with animations
  disabled and the dev overlay hidden (`e2e/hide-dev-overlay.css`). The allowance is a fixed 50
  pixels, never a ratio: a ratio forgives more on a bigger page, and 0.1% of a desktop page hid a
  whole missing input outline. After an intended visual change, run
  `npx playwright test e2e/entry.spec.ts --update-snapshots=all`, look at every changed image, and
  commit them with the change. Baselines are per platform (`-linux`).
- **Run the suite once per API start.** The API allows 30 registrations per IP and
  `e2e/global-setup.ts` clears the count only at the start, so `--repeat-each` across every spec
  runs out; repeat a single spec instead.
- **Prove a regression test**: break the fix on purpose, watch the test fail, then restore it.
- **A page under test must not fail**: no uncaught exception, no console error, no 5xx response.
  The browser's own "Failed to load resource" line for an expected 401 is not a failure.
