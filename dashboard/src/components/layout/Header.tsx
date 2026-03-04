import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/ThemeToggle";
import { isAuthEnabled } from "@/lib/auth";
import { useAuth } from "@/lib/AuthContext";
import type { PhaseStatus } from "@/lib/types";

interface HeaderProps {
  title: string;
  phaseStatus?: PhaseStatus;
  /** Toggle the mobile sidebar drawer. */
  onMenuClick?: () => void;
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

function UserAvatar() {
  if (!isAuthEnabled()) {
    return (
      <Avatar className="h-8 w-8">
        <AvatarFallback className="text-xs">CC</AvatarFallback>
      </Avatar>
    );
  }

  return <AuthenticatedAvatar />;
}

function AuthenticatedAvatar() {
  const { signOut } = useAuth();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" className="rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">CC</AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={signOut}>Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function Header({ title, phaseStatus, onMenuClick }: HeaderProps) {
  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-4 md:px-6">
      <div className="flex items-center gap-3">
        {/* Hamburger — mobile only */}
        {onMenuClick && (
          <button
            type="button"
            onClick={onMenuClick}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground md:hidden"
            aria-label="Open navigation menu"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </button>
        )}
        <h1 className="text-lg font-semibold">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        {phaseStatus && (
          <Badge variant={STATUS_VARIANT[phaseStatus] ?? "outline"}>
            {STATUS_LABEL[phaseStatus] ?? phaseStatus}
          </Badge>
        )}
        <ThemeToggle />
        <UserAvatar />
      </div>
    </header>
  );
}
