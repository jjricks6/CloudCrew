import { useCallback } from "react";
import { useDropzone } from "react-dropzone";

const ACCEPTED_TYPES: Record<string, string[]> = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
    ".docx",
  ],
  "text/markdown": [".md"],
  "text/plain": [".txt"],
  "image/*": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
};

interface UploadZoneProps {
  onUpload: (file: File) => void;
  isUploading?: boolean;
}

export function UploadZone({ onUpload, isUploading }: UploadZoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) {
        onUpload(accepted[0]);
      }
    },
    [onUpload],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxFiles: 1,
    disabled: isUploading,
  });

  return (
    <div
      {...getRootProps()}
      className={`cursor-pointer rounded-md border-2 border-dashed p-4 text-center text-sm transition-colors ${
        isDragActive
          ? "border-primary bg-primary/5"
          : "border-muted-foreground/25 hover:border-primary/50"
      } ${isUploading ? "pointer-events-none opacity-50" : ""}`}
    >
      <input {...getInputProps()} />
      {isUploading ? (
        <p className="text-muted-foreground">Uploading...</p>
      ) : isDragActive ? (
        <p className="text-primary">Drop file here</p>
      ) : (
        <p className="text-muted-foreground">
          Drop a file here or click to upload (PDF, DOCX, MD, TXT, images)
        </p>
      )}
    </div>
  );
}
