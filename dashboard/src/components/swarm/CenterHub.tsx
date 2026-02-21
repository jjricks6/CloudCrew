/**
 * Center hub of the swarm visualization.
 * Shows current phase name and status badge.
 */

import { Badge } from "@/components/ui/badge";
import type { Phase, PhaseStatus } from "@/lib/types";
import { PHASE_LABELS } from "./swarm-constants";

const STATUS_LABELS: Record<string, string> = {
  IN_PROGRESS: "In Progress",
  AWAITING_APPROVAL: "Awaiting Review",
  APPROVED: "Approved",
  REVISION_REQUESTED: "Revision",
};

interface CenterHubProps {
  phase?: Phase;
  phaseStatus?: PhaseStatus;
  cx: number;
  cy: number;
}

export function CenterHub({ phase, phaseStatus, cx, cy }: CenterHubProps) {
  const label = phase ? (PHASE_LABELS[phase] ?? phase) : "—";
  const statusLabel = phaseStatus
    ? (STATUS_LABELS[phaseStatus] ?? phaseStatus)
    : "";

  return (
    <div
      className="absolute flex flex-col items-center justify-center"
      style={{
        left: cx,
        top: cy,
        transform: "translate(-50%, -50%)",
      }}
    >
      <span className="text-lg font-semibold text-foreground">{label}</span>
      {statusLabel && (
        <Badge
          variant={
            phaseStatus === "AWAITING_APPROVAL" ? "outline" : "secondary"
          }
          className="mt-1 text-[10px]"
        >
          {statusLabel}
        </Badge>
      )}
    </div>
  );
}
