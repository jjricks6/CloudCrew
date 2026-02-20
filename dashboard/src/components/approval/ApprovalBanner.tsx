import { useNavigate } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Phase, PhaseStatus } from "@/lib/types";

interface ApprovalBannerProps {
  currentPhase: Phase | undefined;
  phaseStatus: PhaseStatus | undefined;
}

export function ApprovalBanner({
  currentPhase,
  phaseStatus,
}: ApprovalBannerProps) {
  const navigate = useNavigate();

  if (phaseStatus !== "AWAITING_APPROVAL" || !currentPhase) return null;

  return (
    <div className="flex items-center justify-between rounded-lg border border-yellow-500/30 bg-yellow-50 px-4 py-3 dark:bg-yellow-950/20">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-yellow-800 dark:text-yellow-300">
          The {currentPhase} phase is ready for your review.
        </span>
        <Badge variant="secondary" className="text-xs">
          Awaiting Approval
        </Badge>
      </div>
      <Button size="sm" onClick={() => navigate("chat")}>
        Review
      </Button>
    </div>
  );
}
