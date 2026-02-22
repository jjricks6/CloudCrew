import { NavLink } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useAgentStore } from "@/state/stores/agentStore";
import { PHASE_ORDER, type Phase, type PhaseStatus } from "@/lib/types";

const NAV_ITEMS = [
  { to: ".", label: "Dashboard", icon: "grid" },
  { to: "chat", label: "Chat", icon: "message" },
  { to: "board", label: "Board", icon: "kanban" },
  { to: "artifacts", label: "Artifacts", icon: "folder" },
] as const;

const ICON_MAP: Record<string, string> = {
  grid: "M4 5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5Zm10 0a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1V5ZM4 15a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-4Zm10 0a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-4Z",
  message:
    "M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2Z",
  kanban:
    "M6 3a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1H6Zm4.5 0a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1h-3Zm5 0a1 1 0 0 0-1 1v13a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1h-3Z",
  folder:
    "M3 4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2H3Z",
};

interface SidebarProps {
  projectName: string;
  currentPhase?: Phase;
  phaseStatus?: PhaseStatus;
  isOnboarding?: boolean;
}

function getDotColor(
  dotIndex: number,
  currentIndex: number,
  phaseStatus?: PhaseStatus,
): string {
  if (dotIndex < currentIndex) return "bg-green-500";
  if (dotIndex === currentIndex) {
    if (phaseStatus === "AWAITING_APPROVAL" || phaseStatus === "AWAITING_INPUT")
      return "bg-yellow-500";
    if (phaseStatus === "APPROVED") return "bg-green-500";
    return "bg-blue-500";
  }
  return "bg-muted";
}

function PhaseIndicator({
  currentPhase,
  phaseStatus,
}: {
  currentPhase: Phase | undefined;
  phaseStatus: PhaseStatus | undefined;
}) {
  const currentIndex = currentPhase
    ? PHASE_ORDER.indexOf(currentPhase)
    : -1;
  // Align bar fill with dot positions: justify-between places dots at
  // 0%, 25%, 50%, 75%, 100% — so progress must use the same scale.
  const progress =
    currentIndex >= 0
      ? (currentIndex / (PHASE_ORDER.length - 1)) * 100
      : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Phase Progress</span>
        <span>
          {currentIndex + 1}/{PHASE_ORDER.length}
        </span>
      </div>
      <Progress value={progress} className="h-1.5" />
      <div className="flex justify-between">
        {PHASE_ORDER.map((phase, i) => (
          <div
            key={phase}
            className={`h-2 w-2 rounded-full ${getDotColor(i, currentIndex, phaseStatus)}`}
            title={phase}
          />
        ))}
      </div>
    </div>
  );
}

export function Sidebar({
  projectName,
  currentPhase,
  phaseStatus,
  isOnboarding,
}: SidebarProps) {
  const hasNotification = useAgentStore(
    (s) => s.pendingInterrupt !== null || s.pendingApproval !== null,
  );

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-sidebar text-sidebar-foreground">
      {/* Brand header */}
      <div className="border-b p-4">
        <h2 className="text-lg font-bold tracking-tight">CloudCrew</h2>
      </div>

      {/* Project + phase progress */}
      <div className="border-b p-4 space-y-3">
        <div>
          <p className="truncate text-sm font-medium">{projectName}</p>
          {currentPhase && (
            <Badge variant="secondary" className="mt-1 text-xs">
              {currentPhase}
              {phaseStatus === "AWAITING_APPROVAL" && " — Review"}
              {phaseStatus === "AWAITING_INPUT" && " — Input Needed"}
            </Badge>
          )}
        </div>
        {isOnboarding ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Project Setup</span>
            </div>
            <Progress value={0} className="h-1.5" />
          </div>
        ) : (
          <PhaseIndicator currentPhase={currentPhase} phaseStatus={phaseStatus} />
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map(({ to, label, icon }) => {
          const disabled = isOnboarding && to !== ".";
          return (
            <NavLink
              key={to}
              to={to}
              end={to === "."}
              tabIndex={disabled ? -1 : undefined}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                  disabled
                    ? "pointer-events-none cursor-default opacity-40"
                    : isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                      : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                }`
              }
            >
              <svg
                className="h-4 w-4 shrink-0"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d={ICON_MAP[icon]} />
              </svg>
              <span className="relative">
                {label}
                {label === "Chat" && hasNotification && (
                  <span className="absolute -top-1 -right-2.5 h-2 w-2 rounded-full bg-red-500" />
                )}
              </span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t p-4 text-xs text-muted-foreground">
        CloudCrew
      </div>
    </aside>
  );
}
