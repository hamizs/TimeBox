const taskList = document.getElementById('task-list');
const taskForm = document.getElementById('task-form');
const loading = document.getElementById('loading');
const statusMessage = document.getElementById('status-message');
const searchInput = document.getElementById('search');
const filterBy = document.getElementById('filter_by');
const sortBy = document.getElementById('sort_by');
const direction = document.getElementById('direction');
const slowLoad = document.getElementById('slow-load');
let searchTimer = null;
let delayedMode = false;

function localDateTimeToISO(value) {
  if (!value) return '';
  return new Date(value).toISOString();
}

function prettyDate(value) {
  return new Date(value).toLocaleString();
}

function badgeClass(status) {
  if (status === 'Overdue') return 'badge overdue';
  if (status === 'Due Today') return 'badge today';
  if (status === 'Completed') return 'badge completed';
  return 'badge upcoming';
}

async function fetchTasks() {
  loading.classList.remove('hidden');
  const params = new URLSearchParams({
    search: searchInput.value,
    filter_by: filterBy.value,
    sort_by: sortBy.value,
    direction: direction.value,
  });
  if (delayedMode) params.set('delay_ms', '900');
  const response = await fetch(`/api/tasks?${params.toString()}`);
  if (!response.ok) {
    statusMessage.textContent = 'Could not load tasks.';
    loading.classList.add('hidden');
    return;
  }
  const data = await response.json();
  renderTasks(data.items);
  loading.classList.add('hidden');
  delayedMode = false;
}

function renderTasks(items) {
  if (!items.length) {
    taskList.innerHTML = '<article class="task-item"><p>No tasks found.</p></article>';
    return;
  }
  taskList.innerHTML = items.map(task => `
    <article class="task-item" data-task-id="${task.id}">
      <header>
        <div>
          <h3>${escapeHtml(task.title)}</h3>
          <div class="meta">
            <span>${escapeHtml(task.description || 'No description')}</span>
            <span>Due: ${prettyDate(task.due_at)}</span>
          </div>
        </div>
        <span class="${badgeClass(task.status)}" data-testid="task-status">${task.status}</span>
      </header>
      <div class="task-actions">
        <button class="secondary-btn complete-btn">${task.completed ? 'Mark Active' : 'Mark Complete'}</button>
        <button class="secondary-btn delete-btn">Delete</button>
      </div>
    </article>
  `).join('');
}

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function createTask(event) {
  event.preventDefault();
  statusMessage.textContent = '';
  const payload = {
    title: document.getElementById('title').value,
    description: document.getElementById('description').value,
    due_at: localDateTimeToISO(document.getElementById('due_at').value),
  };
  const response = await fetch('/api/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Could not create task.' }));
    statusMessage.textContent = error.detail || 'Could not create task.';
    return;
  }
  taskForm.reset();
  statusMessage.textContent = 'Task created.';
  await fetchTasks();
}

async function handleTaskAction(event) {
  const article = event.target.closest('[data-task-id]');
  if (!article) return;
  const taskId = article.dataset.taskId;
  if (event.target.classList.contains('delete-btn')) {
    await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    statusMessage.textContent = 'Task deleted.';
    await fetchTasks();
    return;
  }
  if (event.target.classList.contains('complete-btn')) {
    const title = article.querySelector('h3').textContent;
    const dueText = article.querySelector('.meta').children[1].textContent.replace('Due: ', '');
    const dueISO = new Date(dueText).toISOString();
    const completed = event.target.textContent.trim() === 'Mark Complete';
    await fetch(`/api/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, due_at: dueISO, completed }),
    });
    statusMessage.textContent = 'Task updated.';
    await fetchTasks();
  }
}

function debounceFetch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => fetchTasks(), 350);
}

taskForm?.addEventListener('submit', createTask);
taskList?.addEventListener('click', handleTaskAction);
searchInput?.addEventListener('input', debounceFetch);
filterBy?.addEventListener('change', fetchTasks);
sortBy?.addEventListener('change', fetchTasks);
direction?.addEventListener('change', fetchTasks);
slowLoad?.addEventListener('click', () => { delayedMode = true; fetchTasks(); });
fetchTasks();
