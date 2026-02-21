import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { queryClient } from "@/state/queryClient";
import { AppLayout } from "@/components/layout/AppLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { ChatPage } from "@/pages/ChatPage";
import { BoardPage } from "@/pages/BoardPage";
import { ArtifactsPage } from "@/pages/ArtifactsPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { isAuthEnabled } from "@/lib/auth";
import { AuthProvider, useAuth } from "@/lib/AuthContext";

/**
 * When Cognito auth is enabled, gates all routes behind authentication.
 * Shows LoginPage when not signed in, renders children when authenticated.
 * When auth is disabled (demo mode / GitHub Pages), renders children directly.
 */
function AuthGate({ children }: { children: React.ReactNode }) {
  const { loading, session } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!session) {
    return <LoginPage />;
  }

  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="/project/demo" replace />} />
      <Route path="/project/:projectId" element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="board" element={<BoardPage />} />
        <Route path="artifacts" element={<ArtifactsPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default function App() {
  const authEnabled = isAuthEnabled();

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <BrowserRouter basename={import.meta.env.BASE_URL}>
              {authEnabled ? (
                <AuthProvider>
                  <AuthGate>
                    <AppRoutes />
                  </AuthGate>
                </AuthProvider>
              ) : (
                <AppRoutes />
              )}
            </BrowserRouter>
          </TooltipProvider>
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
