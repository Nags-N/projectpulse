import { formatEventTime, isSameDisplayDay } from "../time";

function eventIcon(eventType) {
  if (!eventType) return "•";
  if (eventType.startsWith("GIT")) return "⎇";
  if (eventType.startsWith("BUILD")) return "⚙";
  if (eventType.startsWith("FILE")) return "📄";
  return "•";
}

function activityLines(event) {
  const raw = event.display_title || event.title || "";
  return raw.split("\n").filter(Boolean);
}

export default function ActivityTimeline({ events, emptyMessage = "No events yet." }) {
  if (!events || events.length === 0) {
    return <p className="empty-state">{emptyMessage}</p>;
  }

  return (
    <div className="timeline">
      {events.map((event) => {
        const includeDate = !isSameDisplayDay(event.timestamp);
        const lines = activityLines(event);
        return (
          <div key={event.event_id} className="timeline__item">
            <div className="timeline__marker">{eventIcon(event.event_type)}</div>
            <div className="timeline__content">
              <div className="timeline__time">
                {formatEventTime(event.timestamp, { includeDate })}
              </div>
              <div className="timeline__title">
                {lines.map((line) => (
                  <div key={line}>{line}</div>
                ))}
              </div>
              {event.human_description &&
                event.event_type?.startsWith("GIT") &&
                event.human_description !== event.title && (
                  <p className="timeline__description">{event.human_description}</p>
                )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
