import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, ArtifactOut } from "../api";

export function ArtifactViewer({
  artifactId,
  onClose,
}: {
  artifactId: string;
  onClose: () => void;
}) {
  const [artifact, setArtifact] = useState<ArtifactOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setArtifact(null);
    setError(null);

    api
      .getArtifact(artifactId)
      .then((a) => !cancelled && setArtifact(a))
      .catch((e) => !cancelled && setError(e.message || "Failed to load artifact"));

    return () => {
      cancelled = true;
    };
  }, [artifactId]);

  const handleCopy = async () => {
    if (!artifact) return;
    await navigator.clipboard.writeText(artifact.content);
  };

  return (
    <div className="artifact-pane">
      <div className="artifact-header">
        <div className="artifact-info">
          <span className="artifact-title">{artifact ? artifact.title : "Loading artifact…"}</span>
          {artifact && (
            <span className={`artifact-kind ${artifact.kind}`}>
              {artifact.kind}
              {artifact.sanitized ? " · sanitized" : ""}
            </span>
          )}
        </div>
        <div className="artifact-actions">
          <button className="icon-btn" title="Copy content" onClick={handleCopy}>
            📋
          </button>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>
      </div>

      {error && <div className="empty-state">Couldn't load artifact: {error}</div>}

      {!error && !artifact && <div className="empty-state">Loading…</div>}

      {artifact && artifact.kind === "html" && (
        <div className="artifact-body">
          <iframe
            className="artifact-frame"
            title={artifact.title}
            sandbox=""
            srcDoc={artifact.content}
          />
        </div>
      )}

      {artifact && artifact.kind === "markdown" && (
        <div className="artifact-body artifact-body-markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{artifact.content}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}