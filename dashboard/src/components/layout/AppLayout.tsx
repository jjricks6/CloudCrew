import { useState, useCallback } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { useProjectId } from "@/lib/useProjectId";
import { isDemoMode } from "@/lib/demo";
import { useProjectStatus } from "@/state/queries/useProjectQueries";
import { useOnboardingStore } from "@/state/stores/onboardingStore";
import {
  useDemoControlStore,
  DEMO_PHASES,
  DEMO_PHASE_LABELS,
} from "@/state/stores/demoControlStore";
import { useCloudCrewSocket } from "@/state/websocket/useCloudCrewSocket";
import { useDemoEngine } from "@/hooks/useDemoEngine";

/** Map the last path segment to a page title. */
function getPageTitle(pathname: string): string {
  const segment = pathname.split("/").filter(Boolean).pop() ?? "";
  const titles: Record<string, string> = {
    chat: "Project Manager Chat",
    board: "Task Board",
    artifacts: "Artifacts",
  };
  return titles[segment] ?? "Dashboard";
}

const btnClass =
  "rounded px-1.5 py-0.5 text-[11px] font-medium text-amber-700 enabled:hover:bg-amber-200/60 disabled:opacity-40 dark:text-amber-400 dark:enabled:hover:bg-amber-900/40 md:px-2 md:py-1 md:text-xs";

function DemoControls() {
  const currentPhase = useDemoControlStore((s) => s.currentPhase);
  const requestJump = useDemoControlStore((s) => s.requestJump);

  const idx = DEMO_PHASES.indexOf(currentPhase);
  const canRewind = idx > 0;
  const canFF = idx < DEMO_PHASES.length - 1;

  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        onClick={() => requestJump("onboarding")}
        className={btnClass}
        title="Restart demo from beginning"
      >
        &#8634; Restart
      </button>
      <span className="text-amber-300 dark:text-amber-700">|</span>
      <button
        type="button"
        onClick={() => canRewind && requestJump(DEMO_PHASES[idx - 1])}
        disabled={!canRewind}
        className={btnClass}
        title={canRewind ? `Back to ${DEMO_PHASE_LABELS[DEMO_PHASES[idx - 1]]}` : "At first phase"}
      >
        &#9664; Previous Phase
      </button>
      <button
        type="button"
        onClick={() => canFF && requestJump(DEMO_PHASES[idx + 1])}
        disabled={!canFF}
        className={btnClass}
        title={canFF ? `Skip to ${DEMO_PHASE_LABELS[DEMO_PHASES[idx + 1]]}` : "At last phase"}
      >
        Next Phase &#9654;
      </button>
    </div>
  );
}

export function AppLayout() {
  const { pathname } = useLocation();
  const projectId = useProjectId();
  const title = getPageTitle(pathname);
  const demo = isDemoMode(projectId);
  const onboardingStatus = useOnboardingStore((s) => s.status);
  const isOnboarding = onboardingStatus !== "completed";
  const { data: project } = useProjectStatus(projectId);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const toggleSidebar = useCallback(() => setSidebarOpen((prev) => !prev), []);

  // Connect WebSocket for real-time events (no-op in demo mode — socketUrl is null when WS_URL is empty)
  useCloudCrewSocket(demo ? undefined : projectId);
  // Run consolidated demo engine (seeds agents, drives swarm, fires interrupts/approvals)
  useDemoEngine(projectId);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        projectName={project?.project_name ?? "CloudCrew"}
        currentPhase={project?.current_phase}
        phaseStatus={project?.phase_status}
        isOnboarding={isOnboarding}
        mobileOpen={sidebarOpen}
        onClose={closeSidebar}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        {demo && (
          <div className="flex items-center justify-between border-b border-amber-500/20 bg-amber-50 px-3 py-1.5 md:px-4 dark:bg-amber-950/30">
            <div className="flex flex-col md:flex-row md:gap-1.5">
              <span className="text-xs font-semibold text-amber-700 dark:text-amber-400">
                Demo Mode
              </span>
              <span className="text-[10px] text-amber-600/80 dark:text-amber-500/80 md:text-xs">
                Simulated responses
              </span>
            </div>
            <DemoControls />
          </div>
        )}
        <Header title={title} onMenuClick={toggleSidebar} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
