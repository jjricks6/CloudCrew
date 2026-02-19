import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

const PAGE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/chat": "PM Chat",
  "/board": "Task Board",
  "/swarm": "Swarm Visualization",
  "/artifacts": "Artifacts",
};

export function AppLayout() {
  const { pathname } = useLocation();
  const title = PAGE_TITLES[pathname] ?? "CloudCrew";

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
