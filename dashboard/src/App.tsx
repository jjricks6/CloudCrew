import { BrowserRouter, Routes, Route } from "react-router-dom";
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
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="board" element={<BoardPage />} />
              <Route path="swarm" element={<SwarmPage />} />
              <Route path="artifacts" element={<ArtifactsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
          </BrowserRouter>
        </TooltipProvider>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}
