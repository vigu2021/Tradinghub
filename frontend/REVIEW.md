# Frontend review

Follow the rules in `../REVIEW.md`. This file lists what to check on this side.

Run from `frontend/`: `npm run format:check`, `npm run typecheck`, `npm run lint`. Read the Playwright
tests rather than running them, unless asked; they need the full stack up.

- **API contract:** requests and parsed responses match the backend's routes and schemas, including
  the `{"error": ...}` shape and amounts sent as strings.
- **Auth:** cookies, token refresh, redirects, and what a signed-out user can reach.
- **Server and client:** code runs on the side it needs, and no secret reaches the browser.
- **Data:** a mutation refreshes everything it changes, and loading and error states are handled.
- **Money:** amounts are never converted to `number`.
- **Tests:** each one fails if its behaviour is removed, and e2e runs stay within the API's rate limits.
