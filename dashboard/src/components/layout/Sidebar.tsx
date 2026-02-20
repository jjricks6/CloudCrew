import { NavLink } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { PHASE_ORDER, type Phase, type PhaseStatus } from "@/lib/types";

const NAV_ITEMS = [
  { to: ".", label: "Dashboard", icon: "grid" },
  { to: "chat", label: "Chat", icon: "message" },
  { to: "board", label: "Board", icon: "kanban" },
  { to: "swarm", label: "Swarm", icon: "cpu" },
  { to: "artifacts", label: "Artifacts", icon: "folder" },
] as const;

const ICON_MAP: Record<string, string> = {
  grid: "M4 5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5Zm10 0a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1V5ZM4 15a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-4Zm10 0a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v4a1 1 0 0 1-1 1h-4a1 1 0 0 1-1-1v-4Z",
  message:
    "M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2Z",
  kanban:
    "M6 3a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1H6Zm4.5 0a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1h-3Zm5 0a1 1 0 0 0-1 1v13a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1h-3Z",
  cpu: "M9 3V1h6v2h3a2 2 0 0 1 2 2v3h2v6h-2v3a2 2 0 0 1-2 2h-3v2H9v-2H6a2 2 0 0 1-2-2v-3H2V8h2V5a2 2 0 0 1 2-2h3Zm-1 5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V8Z",
  folder:
    "M3 4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2H3Z",
};

interface SidebarProps {
  projectName: string;
  currentPhase?: Phase;
  phaseStatus?: PhaseStatus;
}

function PhaseIndicator({
  currentPhase,
}: {
  currentPhase: Phase | undefined;
}) {
  const currentIndex = currentPhase
    ? PHASE_ORDER.indexOf(currentPhase)
    : -1;
  const progress =
    currentIndex >= 0
      ? ((currentIndex + 1) / PHASE_ORDER.length) * 100
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
            className={`h-2 w-2 rounded-full ${
              i <= currentIndex
                ? "bg-primary"
                : "bg-muted"
            }`}
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
}: SidebarProps) {
  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-sidebar text-sidebar-foreground">
      {/* Project header */}
      <div className="border-b p-4">
        <h2 className="truncate text-sm font-semibold">{projectName || "CloudCrew"}</h2>
        {currentPhase && (
          <Badge variant="secondary" className="mt-1 text-xs">
            {currentPhase}
            {phaseStatus === "AWAITING_APPROVAL" && " — Review"}
          </Badge>
        )}
      </div>

      {/* Phase progress */}
      <div className="border-b p-4">
        <PhaseIndicator currentPhase={currentPhase} />
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "."}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
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
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t p-4 text-xs text-muted-foreground">
        CloudCrew Dashboard
      </div>
    </aside>
  );
}
