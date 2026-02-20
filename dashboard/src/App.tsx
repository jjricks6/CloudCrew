import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import { queryClient } from "@/state/queryClient";
import { AppLayout } from "@/components/layout/AppLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { ChatPage } from "@/pages/ChatPage";
import { BoardPage } from "@/pages/BoardPage";
import { SwarmPage } from "@/pages/SwarmPage";
import { ArtifactsPage } from "@/pages/ArtifactsPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <BrowserRouter>
          <Routes>
            {/* Redirect root to a default project for development.
                In production, this will be replaced by a project list or
                Cognito auth flow that resolves the project ID. */}
            <Route index element={<Navigate to="/project/demo" replace />} />
            <Route path="/project/:projectId" element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="board" element={<BoardPage />} />
              <Route path="swarm" element={<SwarmPage />} />
              <Route path="artifacts" element={<ArtifactsPage />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
          </BrowserRouter>
        </TooltipProvider>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
