function formatDate(isoString) {
  if (!isoString) return null;
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("uk-UA", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildTaskPayload(title, description, dueDate) {
  const cleanTitle = (title || "").trim();
  if (!cleanTitle) return null;
  return {
    title: cleanTitle,
    description: (description || "").trim(),
    due_date: dueDate ? new Date(dueDate).toISOString() : null,
  };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { formatDate, buildTaskPayload };
}