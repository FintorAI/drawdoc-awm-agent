import { redirect } from "next/navigation";

/**
 * Legacy runs page - redirect to dashboard (Agent Hub).
 * Runs are now organized under agent-specific routes:
 * - /drawdocs/runs - DrawDocs runs
 * - /disclosure/runs - Disclosure runs
 */
export default function RunsPage() {
  redirect("/dashboard");
}
