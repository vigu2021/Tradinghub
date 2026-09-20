import { execSync } from "node:child_process";

// The suite registers and fails logins from one address, and the API limits both per IP.
const SUITE_IP_COUNTERS = ["register:ip:127.0.0.1", "login:fail:ip:127.0.0.1"];

export default function globalSetup(): void {
  execSync(
    `docker compose exec -T redis redis-cli del ${SUITE_IP_COUNTERS.join(" ")}`,
    { stdio: "ignore" },
  );
}
