import { expect, test as setup } from "@playwright/test";

import { API_URL, PASSWORD, SIGNED_IN, uniqueEmail } from "./support";

/**
 * Registers one user through the API and saves its cookies, so signed-in tests start signed in
 * instead of each going through the form. The auth flows themselves are tested in auth.spec.ts.
 *
 * One shared session per run. Every test starts from the same refresh token, so a run
 * longer than the 15-minute access token would replay it and trip reuse detection; give each
 * worker its own user if runs ever get that long.
 */
setup("sign in once for the signed-in tests", async ({ request }) => {
  const response = await request.post(`${API_URL}/auth/register`, {
    data: { email: uniqueEmail("shared"), password: PASSWORD },
  });
  expect(response.status(), await response.text()).toBe(201);

  await request.storageState({ path: SIGNED_IN });
});
