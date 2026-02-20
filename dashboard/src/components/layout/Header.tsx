import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { PhaseStatus } from "@/lib/types";

interface HeaderProps {
  title: string;
  phaseStatus?: PhaseStatus;
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  IN_PROGRESS: "default",
  AWAITING_APPROVAL: "secondary",
  APPROVED: "outline",
  REVISION_REQUESTED: "destructive",
};

const STATUS_LABEL: Record<string, string> = {
  IN_PROGRESS: "In Progress",
  AWAITING_APPROVAL: "Awaiting Approval",
  APPROVED: "Approved",
  REVISION_REQUESTED: "Revision Requested",
};

export function Header({ title, phaseStatus }: HeaderProps) {
  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-6">
      <h1 className="text-lg font-semibold">{title}</h1>
      <div className="flex items-center gap-3">
        {phaseStatus && (
          <Badge variant={STATUS_VARIANT[phaseStatus] ?? "outline"}>
            {STATUS_LABEL[phaseStatus] ?? phaseStatus}
          </Badge>
        )}
        <ThemeToggle />
        <Avatar className="h-8 w-8">
          <AvatarFallback className="text-xs">CC</AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
