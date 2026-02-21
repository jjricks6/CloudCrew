/**
 * TanStack Query hooks for file upload.
 *
 * In demo mode, simulates a successful upload without hitting S3.
 */

import { useMutation } from "@tanstack/react-query";
import { post } from "@/lib/api";
import { isDemoMode } from "@/lib/demo";

interface UploadUrlResponse {
  upload_url: string;
  key: string;
  filename: string;
}

interface UploadParams {
  file: File;
}

export function useUploadFile(projectId: string | undefined) {
  return useMutation({
    mutationFn: async ({ file }: UploadParams): Promise<UploadUrlResponse> => {
      if (isDemoMode(projectId)) {
        // Simulate a brief upload delay
        await new Promise((r) => setTimeout(r, 800));
        return {
          upload_url: "",
          key: `projects/demo/uploads/${file.name}`,
          filename: file.name,
        };
      }

      // Step 1: Get presigned URL from backend
      const data = await post<UploadUrlResponse>(
        `/projects/${projectId}/upload`,
        {
          filename: file.name,
          content_type: file.type || "application/octet-stream",
        },
      );

      // Step 2: Upload file directly to S3
      await fetch(data.upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type || "application/octet-stream" },
      });

      return data;
    },
  });
}
