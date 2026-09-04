import { useState, KeyboardEvent, useCallback, memo } from "react";
import { UI_LABELS } from "../constants";

type SkillType = "auto" | "qa" | "ship30" | "artifact";

const SKILLS: { id: SkillType; label: string }[] = [
  { id: "auto", label: "Auto" },
  { id: "qa", label: "Grounded Q&A" },
  { id: "ship30", label: "Ship 30/30 essay" },
  { id: "artifact", label: "Artifact" },
];

const Composer = memo(function Composer({
  onSend,
  disabled,
}: {
  onSend: (text: string, skill: SkillType) => void;
  disabled: boolean;
}) {
  const [text, setText] = useState("");
  const [skill, setSkill] = useState<SkillType>("auto");

  const submit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, skill);
    setText("");
  }, [text, skill, disabled, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div>
      <div className="skill-row" role="group" aria-label="Response type">
        {SKILLS.map((s) => (
          <button
            key={s.id}
            className={`skill-chip ${skill === s.id ? "active" : ""}`}
            onClick={() => setSkill(s.id)}
            aria-pressed={skill === s.id}
            title={`Select ${s.label} mode`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="composer">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={UI_LABELS.COMPOSER_PLACEHOLDER}
          aria-label="Message input"
        />
        <button
          onClick={submit}
          disabled={disabled || !text.trim()}
          aria-label="Send message"
        >
          {UI_LABELS.SEND}
        </button>
      </div>
    </div>
  );
});

export { Composer };
