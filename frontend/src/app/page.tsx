import { redirect } from "next/navigation";

/**
 * No landing page yet. Middleware will decide between the dashboard and the login screen once it
 * exists; until then the honest default is the door.
 */
export default function Home() {
  redirect("/login");
}
