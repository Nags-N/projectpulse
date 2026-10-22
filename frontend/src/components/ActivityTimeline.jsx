import { formatEventTime, isSameDisplayDay } from "../time";

function eventIcon(eventType) {
  if (!eventType) return "•";
  if (eventType.startsWith("GIT")) return "🔀";
  if (eventType.startsWith("BUILD")) return "⚙️";
  if (eventType.startsWith("FILE")) return "📄";
  if (eventType.startsWith("TEST")) return "🧪";
  if (eventType.startsWith("QA")) return "🛡️";
  return "•";
}

function activityLines(event) {
  const raw = event.display_title || event.title || "";
  return raw.split("\n").filter(Boolean);
}

export default function ActivityTimeline({ events, emptyMessage = "No telemetry events recorded yet." }) {
  if (!events || events.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "1.5rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>
        {emptyMessage}
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
      {events.map((event) => {
        const includeDate = !isSameDisplayDay(event.timestamp);
        const lines = activityLines(event);

        return (
          <div
            key={event.event_id || Math.random()}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "0.75rem",
              padding: "0.65rem 0.85rem",
              borderRadius: "8px",
              background: "rgba(7, 11, 20, 0.5)",
              border: "1px solid var(--border-subtle)",
              transition: "all 0.15s ease",
            }}
          >
            <div
              style={{
                width: "28px",
                height: "28px",
                borderRadius: "6px",
                background: "rgba(56, 189, 248, 0.12)",
                border: "1px solid rgba(56, 189, 248, 0.3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "0.85rem",
                flexShrink: 0,
              }}
            >
              {eventIcon(event.event_type)}
            </div>

            <div style={{ flex: 1, overflow: "hidden" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" }}>
                <span style={{ fontSize: "0.7rem", fontFamily: "monospace", color: "var(--text-muted)" }}>
                  {formatEventTime(event.timestamp, { includeDate })}
                </span>
                {event.source && (
                  <span className="badge badge--platform" style={{ fontSize: "0.65rem", padding: "0.1rem 0.35rem" }}>
                    {event.source}
                  </span>
                )}
              </div>

              <div style={{ fontSize: "0.84rem", fontWeight: 600, color: "#fff", lineHeight: 1.3 }}>
                {lines.map((line, lIdx) => (
                  <div key={lIdx}>{line}</div>
                ))}
              </div>

              {event.human_description &&
                event.event_type?.startsWith("GIT") &&
                event.human_description !== event.title && (
                  <p style={{ margin: "0.25rem 0 0", fontSize: "0.76rem", color: "var(--text-secondary)" }}>
                    {event.human_description}
                  </p>
                )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
