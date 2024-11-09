export function PreviewTab({ projectPreviewUrl }) {
  if (!projectPreviewUrl) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No preview available
      </div>
    );
  }

  return (
    <iframe
      src={projectPreviewUrl}
      className="w-full h-full border-0"
      title="Project Preview"
    />
  );
}
