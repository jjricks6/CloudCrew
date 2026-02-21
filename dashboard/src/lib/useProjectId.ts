/**
 * Hook to get the current project ID from route params.
 */

import { useParams } from "react-router-dom";

export function useProjectId(): string | undefined {
  const { projectId } = useParams<{ projectId: string }>();
  return projectId;
}
