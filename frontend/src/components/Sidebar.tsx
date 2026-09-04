import { memo } from "react";
import { SessionOut } from "../api";
import { UI_LABELS } from "../constants";
import { formatRelativeDate, truncate } from "../utils";

const Sidebar = memo(function Sidebar({
  sessions,
  activeSessionId,
  onSelect,
  onNewChat,
}: {
  sessions: SessionOut[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
}) {
  return (
    <aside className="sidebar" role="navigation" aria-label="Chat history">
      <div className="sidebar-header">
        <h1>🌱 Lenny</h1>
        <button
          className="new-chat-btn"
          onClick={onNewChat}
          aria-label={UI_LABELS.NEW_CHAT}
          title="Create a new conversation"
        >
          <span>+</span> {UI_LABELS.NEW_CHAT}
        </button>
      </div>
      <div className="sidebar-list">
        {sessions.map((s) => (
          <button
            key={s.id}
            className={`session-item ${s.id === activeSessionId ? "active" : ""}`}
            onClick={() => onSelect(s.id)}
            title={s.title}
            aria-current={s.id === activeSessionId ? "page" : undefined}
          >
            <span className="session-title">{truncate(s.title, 25)}</span>
            <span className="session-time">
              {formatRelativeDate(s.created_at)}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
});

export { Sidebar };
