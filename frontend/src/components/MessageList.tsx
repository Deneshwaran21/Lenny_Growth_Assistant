import { useEffect, useRef, memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { MessageOut } from "../api";
import { UI_LABELS } from "../constants";
import { copyToClipboard } from "../utils";

type DisplayMessage = MessageOut & {
  artifact_id?: string | null;
  isError?: boolean;
};

const UserAvatar = memo(() => (
  <div className="avatar user-avatar" aria-label="User message">
    U
  </div>
));

const BotAvatar = memo(() => (
  <div className="avatar bot-avatar" aria-label="Assistant message">
    🤖
  </div>
));

const CopyButton = memo(({ content }: { content: string }) => {
  const handleCopy = async () => {
    const success = await copyToClipboard(content);
    if (success) {
      alert("Copied to clipboard!");
    }
  };

  return (
    <button
      className="icon-btn"
      onClick={handleCopy}
      title="Copy message"
      aria-label="Copy message to clipboard"
    >
      📋
    </button>
  );
});

export const MessageList = memo(function MessageList({
  messages,
  pending,
  onOpenArtifact,
}: {
  messages: DisplayMessage[];
  pending: boolean;
  onOpenArtifact: (id: string) => void;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, pending]);

  if (messages.length === 0 && !pending) {
    return <div className="empty-state">{UI_LABELS.EMPTY_STATE_MESSAGE}</div>;
  }

  return (
    <div className="messages">
      {messages.map((m) => (
        <div key={m.id} className={`message-row ${m.role}`}>
          {m.role === "assistant" && <BotAvatar />}
          <div className={`message ${m.isError ? "error" : m.role}`}>
            <div className="message-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {m.content}
              </ReactMarkdown>
            </div>

            {m.role === "assistant" && !m.isError && (
              <>
                <div className="message-meta">
                  <CopyButton content={m.content} />
                  {m.provider_used && (
                    <span className="badge" title={`Provider: ${m.provider_used}`}>
                      {m.provider_used}
                    </span>
                  )}
                  {m.skill_used && (
                    <span className="badge" title={`Skill: ${m.skill_used}`}>
                      skill: {m.skill_used}
                    </span>
                  )}
                  {m.artifact_id && (
                    <button
                      className="badge artifact-btn"
                      onClick={() => onOpenArtifact(m.artifact_id!)}
                      title="View artifact"
                    >
                      Open artifact →
                    </button>
                  )}
                </div>

                {m.sources && m.sources.length > 0 && (
                  <div className="sources" role="region" aria-label="Sources">
                    <strong>Sources:</strong>
                    {m.sources.map((s) => (
                      <div key={s.chunk_id} className="source-item">
                        {s.episode_title}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
          {m.role === "user" && <UserAvatar />}
        </div>
      ))}

      {pending && (
        <div className="message-row assistant">
          <BotAvatar />
          <div className="message assistant" aria-busy="true">
            <div className="typing-indicator" aria-label="Assistant is typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
});
