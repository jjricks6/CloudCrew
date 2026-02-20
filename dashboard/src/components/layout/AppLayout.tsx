import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { useProjectId } from "@/lib/useProjectId";
import { isDemoMode } from "@/lib/demo";

/** Map the last path segment to a page title. */
function getPageTitle(pathname: string): string {
  const segment = pathname.split("/").filter(Boolean).pop() ?? "";
  const titles: Record<string, string> = {
    chat: "Project Manager Chat",
    board: "Task Board",
    swarm: "Swarm Visualization",
    artifacts: "Artifacts",
  };
  return titles[segment] ?? "Dashboard";
}

export function AppLayout() {
  const { pathname } = useLocation();
  const projectId = useProjectId();
  const title = getPageTitle(pathname);
  const demo = isDemoMode(projectId);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar projectName={demo ? "CloudCrew Demo" : "CloudCrew"} />
      <div className="flex flex-1 flex-col overflow-hidden">
        {demo && (
          <div className="border-b border-amber-500/20 bg-amber-50 px-4 py-1.5 text-center text-xs text-amber-700 dark:bg-amber-950/30 dark:text-amber-400">
            Demo Mode — responses are simulated. Connect a backend for live data.
          </div>
        )}
        <Header title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
