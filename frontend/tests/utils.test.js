const test = require("node:test");
const assert = require("node:assert/strict");

const { formatDate, buildTaskPayload } = require("../utils.js");

test("formatDate returns null for empty value", () => {
  assert.equal(formatDate(null), null);
  assert.equal(formatDate(""), null);
});

test("formatDate returns null for invalid date", () => {
  assert.equal(formatDate("not-a-date"), null);
});

test("formatDate formats a valid ISO date with year and day", () => {
  const result = formatDate("2026-09-20T12:00:00Z");
  assert.equal(typeof result, "string");
  assert.match(result, /2026/);
  assert.match(result, /20/);
});

test("buildTaskPayload returns null when title is empty or spaces", () => {
  assert.equal(buildTaskPayload("", "desc", ""), null);
  assert.equal(buildTaskPayload("   ", "desc", ""), null);
});

test("buildTaskPayload trims fields and leaves due_date null when empty", () => {
  assert.deepEqual(buildTaskPayload("  Buy milk ", "  2% ", ""), {
    title: "Buy milk",
    description: "2%",
    due_date: null,
  });
});

test("buildTaskPayload converts due date to ISO string", () => {
  const payload = buildTaskPayload("Lab", "", "2026-09-20T12:00:00Z");
  assert.equal(payload.due_date, "2026-09-20T12:00:00.000Z");
});