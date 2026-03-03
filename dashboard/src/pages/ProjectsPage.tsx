import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { post } from "@/lib/api";
import type { ProjectStatus } from "@/lib/types";

export function ProjectsPage() {
  const navigate = useNavigate();

  const [projectName, setProjectName] = useState("");
  const [requirements, setRequirements] = useState("");
  const [error, setError] = useState("");

  const { mutate: createProject, isPending } = useMutation({
    mutationFn: (data: { project_name: string; initial_requirements: string }) =>
      post<ProjectStatus>("/projects", data),
    onSuccess: (response: ProjectStatus) => {
      navigate(`/project/${response.project_id}`);
    },
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "Failed to create project");
    },
  });

  const handleCreateProject = async () => {
    if (!projectName.trim() || !requirements.trim()) {
      setError("Please fill in all fields");
      return;
    }

    setError("");
    createProject({
      project_name: projectName,
      initial_requirements: requirements,
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">CloudCrew</CardTitle>
          <p className="text-sm text-muted-foreground">Create a New Project</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">Project Name</label>
            <Input
              placeholder="e.g., E-Commerce Platform"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              disabled={isPending}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Initial Requirements</label>
            <Textarea
              placeholder="Describe what you want to build..."
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              disabled={isPending}
              className="min-h-32 resize-none"
            />
          </div>

          <Button
            className="w-full"
            onClick={handleCreateProject}
            disabled={isPending || !projectName.trim() || !requirements.trim()}
          >
            {isPending ? "Creating project..." : "Create Project"}
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            Your project will go through Discovery, Architecture, POC, Production, and Handoff phases.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
