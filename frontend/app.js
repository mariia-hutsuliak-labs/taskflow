// The API address is injected at container startup via config.js
// (see frontend/Dockerfile / docker-entrypoint). Falls back to localhost
// for local development without Docker.
const API_URL = window.API_URL || "http://localhost:8000";

const form = document.getElementById("task-form");
const titleInput = document.getElementById("title");
const descriptionInput = document.getElementById("description");
const dueDateInput = document.getElementById("due_date");
const listEl = document.getElementById("task-list");
const errorEl = document.getElementById("error");

function showError(message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
}

function clearError() {
  errorEl.hidden = true;
  errorEl.textContent = "";
}

function formatDate(isoString) {
  if (!isoString) return null;
  const date = new Date(isoString);
  return date.toLocaleString("uk-UA", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderTasks(tasks) {
  listEl.innerHTML = "";

  if (tasks.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent = "Задач поки немає — додай першу вище.";
    listEl.appendChild(empty);
    return;
  }

  for (const task of tasks) {
    const li = document.createElement("li");
    li.className = "task-card" + (task.done ? " done" : "");

    const main = document.createElement("div");
    main.className = "task-main";

    const title = document.createElement("div");
    title.className = "task-title";
    title.textContent = task.title;
    main.appendChild(title);

    if (task.description) {
      const desc = document.createElement("div");
      desc.className = "task-desc";
      desc.textContent = task.description;
      main.appendChild(desc);
    }

    const due = formatDate(task.due_date);
    if (due) {
      const dueEl = document.createElement("div");
      dueEl.className = "task-due";
      dueEl.textContent = "Термін: " + due;
      main.appendChild(dueEl);
    }

    const actions = document.createElement("div");
    actions.className = "task-actions";

    if (!task.done) {
      const completeBtn = document.createElement("button");
      completeBtn.className = "complete";
      completeBtn.textContent = "Виконано";
      completeBtn.onclick = () => completeTask(task.id);
      actions.appendChild(completeBtn);
    }

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "delete";
    deleteBtn.textContent = "Видалити";
    deleteBtn.onclick = () => deleteTask(task.id);
    actions.appendChild(deleteBtn);

    li.appendChild(main);
    li.appendChild(actions);
    listEl.appendChild(li);
  }
}

async function loadTasks() {
  try {
    const response = await fetch(`${API_URL}/tasks`);
    if (!response.ok) throw new Error("Не вдалося завантажити задачі");
    const tasks = await response.json();
    clearError();
    renderTasks(tasks);
  } catch (err) {
    showError(
      "Не вдалося з'єднатися з API (" + API_URL + "). Переконайся, що backend запущений."
    );
  }
}

async function createTask(event) {
  event.preventDefault();
  const payload = {
    title: titleInput.value.trim(),
    description: descriptionInput.value.trim(),
    due_date: dueDateInput.value ? new Date(dueDateInput.value).toISOString() : null,
  };

  if (!payload.title) return;

  try {
    const response = await fetch(`${API_URL}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error("Не вдалося створити задачу");
    form.reset();
    clearError();
    await loadTasks();
  } catch (err) {
    showError("Не вдалося створити задачу. Спробуй ще раз.");
  }
}

async function completeTask(id) {
  try {
    const response = await fetch(`${API_URL}/tasks/${id}/complete`, { method: "PATCH" });
    if (!response.ok) throw new Error("Не вдалося оновити задачу");
    await loadTasks();
  } catch (err) {
    showError("Не вдалося позначити задачу виконаною.");
  }
}

async function deleteTask(id) {
  try {
    const response = await fetch(`${API_URL}/tasks/${id}`, { method: "DELETE" });
    if (!response.ok) throw new Error("Не вдалося видалити задачу");
    await loadTasks();
  } catch (err) {
    showError("Не вдалося видалити задачу.");
  }
}

form.addEventListener("submit", createTask);
loadTasks();
