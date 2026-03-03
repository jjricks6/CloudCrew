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

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

const ALLOWED_MIME_TYPES = new Set([
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
  "text/csv",
  "image/png",
  "image/jpeg",
]);

function validateFile(file: File): void {
  if (file.size > MAX_FILE_SIZE_BYTES) {
    throw new Error(
      `File too large: ${(file.size / 1024 / 1024).toFixed(1)} MB exceeds the 10 MB limit.`,
    );
  }
  if (file.size === 0) {
    throw new Error("File is empty.");
  }
  const mimeType = file.type || "application/octet-stream";
  if (!ALLOWED_MIME_TYPES.has(mimeType)) {
    throw new Error(
      `File type "${mimeType}" is not allowed. Accepted types: PDF, Word, text, markdown, CSV, PNG, JPEG.`,
    );
  }
}

export function useUploadFile(projectId: string | undefined) {
  return useMutation({
    mutationFn: async ({ file }: UploadParams): Promise<UploadUrlResponse> => {
      validateFile(file);

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
