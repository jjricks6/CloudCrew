/**
 * TanStack Query hooks for file upload.
 */

import { useMutation } from "@tanstack/react-query";
import { post } from "@/lib/api";

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
    mutationFn: async ({ file }: UploadParams) => {
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
