export const DISPLAY_TIMEZONE = "Asia/Kolkata";

function parseUtc(timestamp) {
  if (!timestamp) return null;
  const raw = String(timestamp).trim();
  const hasZone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw);
  const date = new Date(hasZone ? raw : `${raw}Z`);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

export function formatEventTime(timestamp, { includeDate = false } = {}) {
  const date = parseUtc(timestamp);
  if (!date) return "";

  const time = date.toLocaleString("en-US", {
    timeZone: DISPLAY_TIMEZONE,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });

  if (!includeDate) return time;

  const day = date.toLocaleString("en-US", {
    timeZone: DISPLAY_TIMEZONE,
    month: "short",
    day: "numeric",
  });
  return `${day}, ${time}`;
}

export function isSameDisplayDay(timestamp, reference = new Date()) {
  const date = parseUtc(timestamp);
  if (!date) return false;
  const opts = { timeZone: DISPLAY_TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit" };
  return (
    date.toLocaleDateString("en-CA", opts) ===
    reference.toLocaleDateString("en-CA", opts)
  );
}
