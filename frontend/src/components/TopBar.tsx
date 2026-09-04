import { memo } from "react";
import { ConfigOut, HealthOut } from "../api";
import { UI_LABELS, STATUS_TYPES } from "../constants";

const TopBar = memo(function TopBar({
  health,
  config,
  provider,
  onProviderChange,
}: {
  health: HealthOut | null;
  config: ConfigOut | null;
  provider: string;
  onProviderChange: (p: string) => void;
}) {
  const statusClass =
    health?.status === STATUS_TYPES.OK
      ? STATUS_TYPES.OK
      : health?.status === STATUS_TYPES.DOWN
        ? STATUS_TYPES.DOWN
        : STATUS_TYPES.DEGRADED;

  return (
    <div className="topbar">
      <div className="topbar-left">
        <span
          className={`status-dot ${statusClass}`}
          aria-label={`System status: ${health?.status || "connecting"}`}
          title={`Status: ${health?.status || "connecting"}`}
        />
        <span className="status-text">
          {health
            ? `${health.knowledge_base_chunks} chunks · ${health.status}`
            : UI_LABELS.STATUS_CONNECTING}
        </span>
      </div>
      <div className="topbar-right">
        <label htmlFor="provider-select" className="provider-label">
          {UI_LABELS.PROVIDER}
        </label>
        <select
          id="provider-select"
          className="provider-select"
          value={provider}
          onChange={(e) => onProviderChange(e.target.value)}
          aria-label={`Select LLM provider (current: ${provider})`}
        >
          {(config?.providers || []).map((p) => (
            <option key={p.provider} value={p.provider}>
              {p.provider}
              {p.provider === "ollama"
                ? p.reachable
                  ? " ✓"
                  : " ✗"
                : p.configured
                  ? ""
                  : " (no key)"}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
});

export { TopBar };
