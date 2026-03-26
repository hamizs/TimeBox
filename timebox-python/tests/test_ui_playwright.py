from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('127.0.0.1', 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope='session')
def live_server():
    port = free_port()
    db_file = ROOT / 'app' / 'data' / 'timebox.db'
    if db_file.exists():
        db_file.unlink()
    proc = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    base_url = f'http://127.0.0.1:{port}'
    for _ in range(80):
        try:
            with urllib.request.urlopen(f'{base_url}/api/health') as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.25)
    else:
        output = proc.stdout.read() if proc.stdout else 'No server output.'
        proc.terminate()
        raise RuntimeError(f'Server did not start. Output: {output}')
    yield base_url
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture()
def page(live_server: str):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(base_url=live_server)
        page = context.new_page()
        yield page
        context.close()
        browser.close()


@pytest.fixture()
def page_with_app(page: Page, live_server: str):
    page.goto(f'{live_server}/register')
    page.get_by_label('Username').fill(f'user{int(time.time() * 1000)}')
    page.get_by_label('Password').fill('secret')
    page.get_by_role('button', name='Create account').click()
    expect(page).to_have_url(f'{live_server}/dashboard')
    page.goto(f'{live_server}/tasks')
    return page


def fill_task_form(page: Page, title: str, desc: str, due_local: str):
    page.locator('#title').fill(title)
    page.locator('#description').fill(desc)
    page.locator('#due_at').fill(due_local)
    page.get_by_role('button', name='Add Task').click()


def test_create_complete_delete_task(page_with_app: Page):
    page = page_with_app
    due_local = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')
    fill_task_form(page, 'Playwright Task', 'UI path', due_local)

    expect(page.get_by_text('Task created.')).to_be_visible()
    item = page.locator('[data-task-id]').filter(has_text='Playwright Task').first
    expect(item).to_be_visible()

    item.get_by_role('button', name='Mark Complete').click()
    expect(item.get_by_test_id('task-status')).to_have_text('Completed')

    item.get_by_role('button', name='Delete').click()
    expect(page.get_by_text('Task deleted.')).to_be_visible()
    expect(page.get_by_text('Playwright Task')).not_to_be_visible()


def test_filter_sort_and_delayed_loading(page_with_app: Page):
    page = page_with_app
    fill_task_form(page, 'Zulu Task', 'sort', (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'))
    fill_task_form(page, 'Alpha Task', 'sort', (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'))

    page.locator('#sort_by').select_option('title')
    expect(page.locator('[data-task-id] h3').first).to_have_text('Alpha Task')

    page.get_by_role('button', name='Load with Delay').click()
    expect(page.get_by_test_id('loading')).to_be_visible()
    expect(page.get_by_test_id('loading')).not_to_be_visible()

    alpha = page.locator('[data-task-id]').filter(has_text='Alpha Task').first
    alpha.get_by_role('button', name='Mark Complete').click()
    page.locator('#filter_by').select_option('completed')
    expect(page.locator('[data-task-id]')).to_have_count(1)
    expect(page.get_by_text('Alpha Task')).to_be_visible()
