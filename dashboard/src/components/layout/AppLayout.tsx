import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

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
  const title = getPageTitle(pathname);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar projectName="CloudCrew" />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
