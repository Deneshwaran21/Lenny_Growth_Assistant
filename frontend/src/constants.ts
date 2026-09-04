export const SKILLS = {
  AUTO: "auto",
  QA: "qa",
  SHIP30: "ship30",
  ARTIFACT: "artifact",
} as const;

export type SkillType = (typeof SKILLS)[keyof typeof SKILLS];

export const SKILL_LABELS = {
  [SKILLS.AUTO]: "Auto",
  [SKILLS.QA]: "Grounded Q&A",
  [SKILLS.SHIP30]: "Ship 30/30 essay",
  [SKILLS.ARTIFACT]: "Artifact",
} as const;

export const UI_LABELS = {
  NEW_CHAT: "New chat",
  SEND: "Send",
  PROVIDER: "Provider",
  STATUS_CONNECTING: "Connecting...",
  COMPOSER_PLACEHOLDER:
    "Ask about product-led growth, activation, pricing... (Enter to send, Shift+Enter for newline)",
  EMPTY_STATE_MESSAGE:
    "Ask a product or growth question grounded in Lenny's Podcast transcripts - e.g. \"What makes a good activation metric?\" - or ask for a Ship 30 for 30 essay or an artifact.",
  BACKEND_ERROR:
    "Can't reach the backend API. Is it running? See README 'Troubleshooting'.",
  SOMETHING_WENT_WRONG: "Something went wrong talking to the assistant.",
} as const;

export const STATUS_TYPES = {
  OK: "ok",
  DOWN: "down",
  DEGRADED: "degraded",
} as const;

export const DEBOUNCE_MS = 300;
export const SCROLL_BEHAVIOR = "smooth" as const;
export const USER_ID_DEMO = "denesh-demo";