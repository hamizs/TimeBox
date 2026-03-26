from __future__ import annotations

import os
import socket
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from playwright.sync_api import Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"
DB_PATH = APP_DIR / "data" / "timebox.db"
SCREENSHOT_DIR = PROJECT_ROOT / "demo_screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)


def log(message: str) -> None:
    print(f"[DEMO] {message}", flush=True)


def step(page: Page, message: str, pause: float = 0.9) -> None:
    log(message)
    try:
        page.locator("body").highlight()
    except Exception:
        pass
    time.sleep(pause)


def find_free_port(start: int = 8000, end: int = 8100) -> int:
    for port in range(start, end + 1):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("Could not find a free local port between 8000 and 8100.")


def reset_database() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
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
        conn.commit()
    finally:
        conn.close()
    log("Database reset complete.")


def start_server(port: int) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    log(f"Starting FastAPI app on port {port}...")
    process = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    wait_for_server(process, port)
    return process


def wait_for_server(process: subprocess.Popen[str], port: int, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    lines: list[str] = []
    while time.time() < deadline:
        if process.poll() is not None:
            output = "".join(lines)
            raise RuntimeError(f"Server exited early.\n{output}")
        line = process.stdout.readline() if process.stdout else ""
        if line:
            lines.append(line)
            print(line, end="")
            if "Application startup complete" in line or f"Uvicorn running on http://127.0.0.1:{port}" in line:
                time.sleep(0.5)
                return
        time.sleep(0.1)
    raise RuntimeError("Timed out waiting for the FastAPI server to start.")


def stop_server(process: subprocess.Popen[str] | None) -> None:
    if not process:
        return
    log("Stopping FastAPI app...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def unique_username() -> str:
    return f"demo_user_{int(time.time())}"


def register_user(page: Page, base_url: str, username: str, password: str) -> None:
    page.goto(f"{base_url}/register", wait_until="networkidle")
    step(page, "Opened the Register page.")
    page.get_by_placeholder("Username").fill(username)
    step(page, f"Typed username: {username}", 0.7)
    page.get_by_placeholder("Password").fill(password)
    step(page, "Typed a password.", 0.7)
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/dashboard")
    step(page, "Submitted the form and landed on the Dashboard page.")
    page.screenshot(path=str(SCREENSHOT_DIR / "01_register_dashboard.png"), full_page=True)


def logout_user(page: Page) -> None:
    page.get_by_role("button", name="Logout").click()
    page.wait_for_url("**/")
    step(page, "Logged out and returned to the Home page.")


def login_user(page: Page, base_url: str, username: str, password: str) -> None:
    page.goto(f"{base_url}/login", wait_until="networkidle")
    step(page, "Opened the Login page.")
    page.get_by_placeholder("Username").fill(username)
    page.get_by_placeholder("Password").fill(password)
    step(page, "Entered valid login credentials.")
    page.get_by_role("button", name="Login").click()
    page.wait_for_url("**/dashboard")
    step(page, "Signed in successfully and reached the Dashboard.")
    page.screenshot(path=str(SCREENSHOT_DIR / "02_login_dashboard.png"), full_page=True)


def go_to_tasks(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/tasks", wait_until="networkidle")
    page.wait_for_selector("#task-form")
    step(page, "Opened the Task Manager page.")


def add_task(page: Page, title: str, description: str, due_dt: datetime) -> None:
    page.locator("#title").fill(title)
    page.locator("#description").fill(description)
    page.locator("#due_at").fill(due_dt.astimezone().strftime("%Y-%m-%dT%H:%M"))
    step(page, f"Filled task form for: {title}", 0.8)
    page.get_by_role("button", name="Add Task").click()
    page.locator("text=Task created.").wait_for()
    page.locator(f"article.task-item:has-text('{title}')").wait_for()
    step(page, f"Created task: {title}")


def test_01_register_and_dashboard(playwright: Playwright, base_url: str, username: str, password: str) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=400)
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    try:
        register_user(page, base_url, username, password)
        due_today = page.get_by_test_id("due-today-count").inner_text()
        overdue = page.get_by_test_id("overdue-count").inner_text()
        completed = page.get_by_test_id("completed-count").inner_text()
        log(f"Dashboard counts after registration -> Due Today: {due_today}, Overdue: {overdue}, Completed: {completed}")
        time.sleep(1.0)
    finally:
        context.close()
        browser.close()


def test_02_login_flow(playwright: Playwright, base_url: str, username: str, password: str) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=400)
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    try:
        login_user(page, base_url, username, password)
        logout_user(page)
        login_user(page, base_url, username, password)
        time.sleep(1.0)
    finally:
        context.close()
        browser.close()


def test_03_create_tasks_and_sort(playwright: Playwright, base_url: str, username: str, password: str) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=400)
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    try:
        login_user(page, base_url, username, password)
        go_to_tasks(page, base_url)
        now = datetime.now(timezone.utc)
        add_task(page, "Alpha planning", "First task for alphabetical sort", now + timedelta(hours=3))
        add_task(page, "Beta review", "Second task due later today", now + timedelta(hours=5))
        add_task(page, "Legacy cleanup", "This one should already be overdue", now - timedelta(days=1))
        titles = page.locator("article.task-item h3")
        assert titles.count() >= 3, "Expected at least three tasks after creation."
        step(page, "Verified that multiple tasks now appear in the task list.")

        page.locator("#sort_by").select_option("title")
        step(page, "Changed sort mode to Title.")
        first_title = titles.nth(0).inner_text()
        assert first_title == "Alpha planning", f"Expected Alpha planning first after title sort, got {first_title!r}"

        page.locator("#direction").select_option("desc")
        step(page, "Changed sort direction to Descending.")
        first_title_desc = titles.nth(0).inner_text()
        assert first_title_desc == "Legacy cleanup", f"Expected Legacy cleanup first after descending title sort, got {first_title_desc!r}"

        page.screenshot(path=str(SCREENSHOT_DIR / "03_tasks_created_and_sorted.png"), full_page=True)
        time.sleep(1.0)
    finally:
        context.close()
        browser.close()


def test_04_search_and_filters(playwright: Playwright, base_url: str, username: str, password: str) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=400)
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    try:
        login_user(page, base_url, username, password)
        go_to_tasks(page, base_url)

        page.locator("#search").fill("Legacy")
        step(page, "Typed into the search box to find a specific task.")
        page.wait_for_timeout(800)
        visible_titles = page.locator("article.task-item h3")
        assert visible_titles.count() == 1, "Expected a single search result for Legacy."
        assert visible_titles.first.inner_text() == "Legacy cleanup"
        page.screenshot(path=str(SCREENSHOT_DIR / "04_search_result.png"), full_page=True)

        page.locator("#search").fill("")
        page.wait_for_timeout(800)
        step(page, "Cleared the search box and reloaded all tasks.")

        page.locator("#filter_by").select_option("overdue")
        step(page, "Filtered the list to show only overdue tasks.")
        overdue_badges = page.get_by_test_id("task-status")
        assert overdue_badges.count() >= 1
        assert all(overdue_badges.nth(i).inner_text() == "Overdue" for i in range(overdue_badges.count()))

        page.locator("#filter_by").select_option("all")
        page.wait_for_timeout(600)
        step(page, "Returned to the full task list.")
        time.sleep(1.0)
    finally:
        context.close()
        browser.close()


def test_05_complete_reactivate_and_dashboard(playwright: Playwright, base_url: str, username: str, password: str) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=400)
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    try:
        login_user(page, base_url, username, password)
        go_to_tasks(page, base_url)

        target = page.locator("article.task-item", has_text="Alpha planning")
        target.get_by_role("button", name="Mark Complete").click()
        page.locator("text=Task updated.").wait_for()
        step(page, "Marked Alpha planning as completed.")
        target.get_by_test_id("task-status").wait_for()
        assert target.get_by_test_id("task-status").inner_text() == "Completed"
        page.screenshot(path=str(SCREENSHOT_DIR / "05_completed_task.png"), full_page=True)

        page.locator("#filter_by").select_option("completed")
        step(page, "Filtered to only completed tasks.")
        assert page.locator("article.task-item h3").first.inner_text() == "Alpha planning"

        page.goto(f"{base_url}/dashboard", wait_until="networkidle")
        step(page, "Returned to the Dashboard to verify updated counts.")
        completed_count = int(page.get_by_test_id("completed-count").inner_text())
        assert completed_count >= 1

        page.goto(f"{base_url}/tasks", wait_until="networkidle")
        page.locator("#filter_by").select_option("completed")
        page.locator("article.task-item", has_text="Alpha planning").get_by_role("button", name="Mark Active").click()
        page.locator("text=Task updated.").wait_for()
        step(page, "Reactivated the completed task back to active.")
        page.locator("#filter_by").select_option("all")
        time.sleep(1.0)
    finally:
        context.close()
        browser.close()


def test_06_delayed_load_and_delete(playwright: Playwright, base_url: str, username: str, password: str) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=400)
    context = browser.new_context(viewport={"width": 1440, "height": 960})
    page = context.new_page()
    try:
        login_user(page, base_url, username, password)
        go_to_tasks(page, base_url)

        page.locator("#slow-load").click()
        step(page, "Clicked the delayed load button to simulate slower task loading.")
        page.get_by_test_id("loading").wait_for(state="visible")
        page.get_by_test_id("loading").wait_for(state="hidden")
        step(page, "Observed the loading indicator appear and disappear.")
        page.screenshot(path=str(SCREENSHOT_DIR / "06_delayed_load.png"), full_page=True)

        delete_target = page.locator("article.task-item", has_text="Beta review")
        delete_target.get_by_role("button", name="Delete").click()
        page.locator("text=Task deleted.").wait_for()
        step(page, "Deleted the Beta review task.")
        page.locator("article.task-item", has_text="Beta review").wait_for(state="hidden")
        page.screenshot(path=str(SCREENSHOT_DIR / "07_after_delete.png"), full_page=True)
        time.sleep(1.0)
    finally:
        context.close()
        browser.close()


def run_test(name: str, func: Callable[..., None], playwright: Playwright, base_url: str, username: str, password: str) -> bool:
    print("\n" + "=" * 78)
    log(f"STARTING {name}")
    print("=" * 78)
    try:
        func(playwright, base_url, username, password)
        log(f"PASSED {name}")
        return True
    except AssertionError as exc:
        log(f"FAILED {name} -> {exc}")
        return False
    except PlaywrightTimeoutError as exc:
        log(f"FAILED {name} -> Playwright timeout: {exc}")
        return False
    except Exception as exc:
        log(f"FAILED {name} -> {type(exc).__name__}: {exc}")
        return False


def main() -> int:
    if not (PROJECT_ROOT / "app" / "main.py").exists():
        print("Place this file in the root of your timebox-python project before running it.")
        return 1

    reset_database()
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    username = unique_username()
    password = "demo1234"
    server: subprocess.Popen[str] | None = None

    tests: list[tuple[str, Callable[..., None]]] = [
        ("Test 1 - Register and view dashboard", test_01_register_and_dashboard),
        ("Test 2 - Login and logout flow", test_02_login_flow),
        ("Test 3 - Create tasks and verify sorting", test_03_create_tasks_and_sort),
        ("Test 4 - Search tasks and apply filters", test_04_search_and_filters),
        ("Test 5 - Complete/reactivate task and verify dashboard", test_05_complete_reactivate_and_dashboard),
        ("Test 6 - Delayed loading and delete task", test_06_delayed_load_and_delete),
    ]

    try:
        server = start_server(port)
        passed = 0
        with sync_playwright() as playwright:
            for name, func in tests:
                if run_test(name, func, playwright, base_url, username, password):
                    passed += 1
                time.sleep(1.0)

        print("\n" + "-" * 78)
        log(f"Finished demo run. Passed {passed} of {len(tests)} tests.")
        log(f"Screenshots saved in: {SCREENSHOT_DIR}")
        print("-" * 78)
        return 0 if passed == len(tests) else 1
    finally:
        stop_server(server)


if __name__ == "__main__":
    raise SystemExit(main())
