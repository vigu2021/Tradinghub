import { redirect } from "next/navigation";

/**
 * No landing page yet. The door is the honest default: the auth layouts take it from here, and
 * a visitor with a live session is moved along to the dashboard.
 */
export default function Home() {
  redirect("/login");
}
