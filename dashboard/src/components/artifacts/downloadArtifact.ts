/** Trigger a browser download of artifact content as a file. */
export function downloadArtifact(gitPath: string, content: string): void {
  const filename = gitPath.split("/").pop() ?? "artifact.md";
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
