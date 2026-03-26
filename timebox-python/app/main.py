from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / 'data'
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / 'timebox.db'

app = FastAPI(title='TimeBox Python')
app.add_middleware(SessionMiddleware, secret_key='timebox-dev-secret-change-me')
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'static')), name='static')
templates = Jinja2Templates(directory=str(BASE_DIR / 'templates'))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_at TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            '''
        )


@app.on_event('startup')
def on_startup() -> None:
    init_db()


init_db()


def current_user_id(request: Request) -> int | None:
    user_id = request.session.get('user_id')
    return int(user_id) if user_id else None


def require_user(request: Request) -> int:
    user_id = current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user_id


def parse_due_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail='Invalid due date') from exc


def task_status(task: sqlite3.Row | dict[str, Any], now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    due = parse_due_dt(task['due_at'])
    completed = bool(task['completed'])
    if completed:
        return 'Completed'
    if due < now:
        return 'Overdue'
    if due.date() == now.date():
        return 'Due Today'
    return 'Upcoming'


def task_to_dict(task: sqlite3.Row) -> dict[str, Any]:
    return {
        'id': task['id'],
        'title': task['title'],
        'description': task['description'],
        'due_at': task['due_at'],
        'completed': bool(task['completed']),
        'created_at': task['created_at'],
        'updated_at': task['updated_at'],
        'status': task_status(task),
    }


def dashboard_counts(conn: sqlite3.Connection, user_id: int) -> dict[str, int]:
    now = datetime.now(timezone.utc)
    rows = conn.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,)).fetchall()
    counts = {'due_today': 0, 'overdue': 0, 'completed': 0}
    for row in rows:
        status = task_status(row, now)
        if status == 'Due Today':
            counts['due_today'] += 1
        elif status == 'Overdue':
            counts['overdue'] += 1
        elif status == 'Completed':
            counts['completed'] += 1
    return counts


@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    if current_user_id(request):
        return RedirectResponse('/dashboard', status_code=303)
    return templates.TemplateResponse(request, 'index.html', {'year': datetime.now().year})


@app.get('/register', response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, 'register.html', {'error': None})


@app.post('/register')
def register(request: Request, username: str = Form(...), password: str = Form(...)):
    if len(password) < 4:
        return templates.TemplateResponse(request, 'register.html', {'error': 'Password must be at least 4 characters.'}, status_code=400)
    with get_db() as conn:
        try:
            cur = conn.execute(
                'INSERT INTO users(username, password_hash, created_at) VALUES (?, ?, ?)',
                (username.strip(), hash_password(password), now_iso()),
            )
        except sqlite3.IntegrityError:
            return templates.TemplateResponse(request, 'register.html', {'error': 'Username already exists.'}, status_code=400)
        request.session['user_id'] = cur.lastrowid
        request.session['username'] = username.strip()
    return RedirectResponse('/dashboard', status_code=303)


@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, 'login.html', {'error': None})


@app.post('/login')
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE username = ?', (username.strip(),)).fetchone()
        if not row or row['password_hash'] != hash_password(password):
            return templates.TemplateResponse(request, 'login.html', {'error': 'Invalid username or password.'}, status_code=400)
        request.session['user_id'] = row['id']
        request.session['username'] = row['username']
    return RedirectResponse('/dashboard', status_code=303)


@app.post('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/', status_code=303)


@app.get('/dashboard', response_class=HTMLResponse)
def dashboard(request: Request):
    user_id = require_user(request)
    with get_db() as conn:
        counts = dashboard_counts(conn, user_id)
    return templates.TemplateResponse(
        request,
        'dashboard.html',
        {'username': request.session.get('username', 'User'), 'counts': counts},
    )


@app.get('/tasks', response_class=HTMLResponse)
def tasks_page(request: Request):
    require_user(request)
    return templates.TemplateResponse(request, 'tasks.html', {'username': request.session.get('username', 'User')})


@app.get('/api/health')
def health():
    return {'ok': True}


@app.get('/api/tasks')
def list_tasks(
    request: Request,
    search: str = '',
    filter_by: str = 'all',
    sort_by: str = 'due_at',
    direction: str = 'asc',
    delay_ms: int = 0,
):
    user_id = require_user(request)
    if delay_ms:
        time.sleep(min(delay_ms, 3000) / 1000)
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,)).fetchall()
    tasks = [task_to_dict(r) for r in rows]

    if search:
        needle = search.lower()
        tasks = [t for t in tasks if needle in t['title'].lower() or needle in t['description'].lower()]

    if filter_by == 'active':
        tasks = [t for t in tasks if not t['completed']]
    elif filter_by == 'completed':
        tasks = [t for t in tasks if t['completed']]
    elif filter_by == 'overdue':
        tasks = [t for t in tasks if t['status'] == 'Overdue']

    reverse = direction == 'desc'
    if sort_by == 'title':
        tasks.sort(key=lambda t: (t['title'].lower(), t['id']), reverse=reverse)
    elif sort_by == 'created_at':
        tasks.sort(key=lambda t: (t['created_at'], t['id']), reverse=reverse)
    else:
        tasks.sort(key=lambda t: (t['due_at'], t['id']), reverse=reverse)

    return {'items': tasks}


@app.post('/api/tasks')
async def create_task(request: Request):
    user_id = require_user(request)
    payload = await request.json()
    title = str(payload.get('title', '')).strip()
    description = str(payload.get('description', '')).strip()
    due_at = str(payload.get('due_at', '')).strip()
    if not title:
        raise HTTPException(status_code=400, detail='Title is required')
    parse_due_dt(due_at)
    created = now_iso()
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO tasks(user_id, title, description, due_at, completed, created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?)',
            (user_id, title, description, due_at, created, created),
        )
        row = conn.execute('SELECT * FROM tasks WHERE id = ?', (cur.lastrowid,)).fetchone()
    return task_to_dict(row)


@app.put('/api/tasks/{task_id}')
async def update_task(task_id: int, request: Request):
    user_id = require_user(request)
    payload = await request.json()
    with get_db() as conn:
        row = conn.execute('SELECT * FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Task not found')
        title = str(payload.get('title', row['title'])).strip()
        description = str(payload.get('description', row['description'])).strip()
        due_at = str(payload.get('due_at', row['due_at'])).strip()
        completed = 1 if payload.get('completed', bool(row['completed'])) else 0
        if not title:
            raise HTTPException(status_code=400, detail='Title is required')
        parse_due_dt(due_at)
        conn.execute(
            'UPDATE tasks SET title = ?, description = ?, due_at = ?, completed = ?, updated_at = ? WHERE id = ? AND user_id = ?',
            (title, description, due_at, completed, now_iso(), task_id, user_id),
        )
        updated = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    return task_to_dict(updated)


@app.delete('/api/tasks/{task_id}')
def delete_task(task_id: int, request: Request):
    user_id = require_user(request)
    with get_db() as conn:
        cur = conn.execute('DELETE FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail='Task not found')
    return {'deleted': True}


@app.get('/api/dashboard')
def api_dashboard(request: Request):
    user_id = require_user(request)
    with get_db() as conn:
        return dashboard_counts(conn, user_id)
