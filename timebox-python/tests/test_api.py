from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

DB_FILE = Path(__file__).resolve().parents[1] / 'app' / 'data' / 'timebox.db'
if DB_FILE.exists():
    DB_FILE.unlink()

from app.main import app  # noqa: E402

client = TestClient(app)


def register_and_login(username: str = 'tester', password: str = 'secret'):
    response = client.post('/register', data={'username': username, 'password': password}, follow_redirects=False)
    assert response.status_code == 303


def test_register_login_and_task_crud_flow():
    register_and_login('api_user', 'secret')

    due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = client.post('/api/tasks', json={'title': 'Write report', 'description': 'For class', 'due_at': due})
    assert response.status_code == 200
    task = response.json()
    assert task['title'] == 'Write report'
    assert task['status'] in {'Upcoming', 'Due Today'}

    response = client.get('/api/tasks')
    assert response.status_code == 200
    items = response.json()['items']
    assert len(items) == 1

    response = client.put(f"/api/tasks/{task['id']}", json={'title': 'Write final report', 'description': 'Updated', 'due_at': due, 'completed': True})
    assert response.status_code == 200
    assert response.json()['completed'] is True
    assert response.json()['status'] == 'Completed'

    dashboard = client.get('/api/dashboard').json()
    assert dashboard['completed'] == 1

    response = client.delete(f"/api/tasks/{task['id']}")
    assert response.status_code == 200
    assert response.json()['deleted'] is True

    response = client.get('/api/tasks')
    assert response.json()['items'] == []
