import { useEffect, useState } from "react";
import { api, ApiError, ConfigOut, HealthOut, MessageOut, SessionOut } from "./api";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { MessageList } from "./components/MessageList";
import { Composer } from "./components/Composer";
import { ArtifactViewer } from "./components/ArtifactViewer";
import { UI_LABELS, USER_ID_DEMO } from "./constants";
import { copyToClipboard } from "./utils";

type DisplayMessage = MessageOut & { artifact_id?: string | null; isError?: boolean };

export default function App() {
  const [sessions, setSessions] = useState<SessionOut[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [health, setHealth] = useState<HealthOut | null>(null);
  const [config, setConfig] = useState<ConfigOut | null>(null);
  const [provider, setProvider] = useState<string>("ollama");
  const [openArtifactId, setOpenArtifactId] = useState<string | null>(null);
  const [initError, setInitError] = useState<string | null>(null);

  // Initial load: health, config, sessions
  useEffect(() => {
    api.health().then(setHealth).catch(() => setInitError(UI_LABELS.BACKEND_ERROR));
    api.config().then((c) => {
      setConfig(c);
      setProvider(c.active_provider);
    }).catch(() => {});

    api.listSessions(USER_ID_DEMO).then(async (existing) => {
      setSessions(existing);
      if (existing.length > 0) {
        setActiveSessionId(existing[0].id);
      } else {
        const created = await api.createSession(USER_ID_DEMO);
        setSessions([created]);
        setActiveSessionId(created.id);
      }
    }).catch(() => setInitError(UI_LABELS.BACKEND_ERROR));
  }, []);

  // Load messages whenever active session changes
  useEffect(() => {
    if (!activeSessionId) return;
    setOpenArtifactId(null);
    api.getMessages(activeSessionId).then(setMessages).catch(() => setMessages([]));
  }, [activeSessionId]);

  const handleNewChat = async () => {
    const created = await api.createSession(USER_ID_DEMO, provider);
    setSessions((prev) => [created, ...prev]);
    setActiveSessionId(created.id);
  };

  const handleSend = async (text: string, skill: "auto" | "qa" | "ship30" | "artifact") => {
    if (!activeSessionId) return;

    const optimisticUserMsg: DisplayMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content: text,
      provider_used: null,
      sources: [],
      skill_used: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUserMsg]);
    setPending(true);

    try {
      const resp = await api.sendMessage(activeSessionId, text, skill, provider);
      const assistantMsg: DisplayMessage = {
        id: resp.message_id,
        role: "assistant",
        content: resp.reply,
        provider_used: resp.provider_used,
        sources: resp.sources,
        skill_used: resp.skill_used,
        created_at: new Date().toISOString(),
        artifact_id: resp.artifact_id,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      if (resp.artifact_id) {
        setOpenArtifactId(resp.artifact_id);
      }
    } catch (e) {
      const message =
        e instanceof ApiError
          ? e.message
          : UI_LABELS.SOMETHING_WENT_WRONG;
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `⚠️ ${message}`,
          provider_used: null,
          sources: [],
          skill_used: null,
          created_at: new Date().toISOString(),
          isError: true,
        },
      ]);
    } finally {
      setPending(false);
    }
  };

  if (initError) {
    return (
      <div className="empty-state" style={{ height: "100vh" }}>
        {initError}
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onNewChat={handleNewChat}
      />
      <div className={`main-area ${openArtifactId ? "with-artifact" : ""}`}>
        <TopBar health={health} config={config} provider={provider} onProviderChange={setProvider} />
        <div className="chat-pane">
          <MessageList messages={messages} pending={pending} onOpenArtifact={setOpenArtifactId} />
          <Composer onSend={handleSend} disabled={pending || !activeSessionId} />
        </div>
        {openArtifactId && (
          <ArtifactViewer artifactId={openArtifactId} onClose={() => setOpenArtifactId(null)} />
        )}
      </div>
    </div>
  );
}
