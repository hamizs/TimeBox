# 🧪 TimeBox – End-to-End Software Testing Project

> A full-stack task reminder application built to demonstrate **reliable vs flaky testing** using FastAPI, Pytest, and Playwright.

---

## 🚀 Overview

TimeBox is a lightweight web application designed to simulate **real-world testing challenges** such as:

* Time-sensitive logic (overdue vs due today)
* Asynchronous UI behavior
* Dynamic data ordering
* Network and rendering delays

The project includes:

* Backend API testing (Pytest)
* UI end-to-end testing (Playwright)
* A **fully automated browser demo script** that visually executes all test scenarios

---

## 🎥 Demo (Automated Browser Execution)

Run a complete visual test demonstration:

```bash
python demo_browser_run.py
```

This will:

* Start the backend automatically
* Launch a real browser
* Execute all user flows step-by-step
* Show interactions (clicks, typing, navigation)
* Print test results (PASS/FAIL)
* Capture screenshots

---

## 🛠 Tech Stack

| Layer      | Technology                             |
| ---------- | -------------------------------------- |
| Backend    | FastAPI                                |
| Frontend   | Jinja Templates, HTML, CSS, JavaScript |
| Database   | SQLite                                 |
| Testing    | Pytest (API), Playwright (UI)          |
| Automation | Python (Playwright Sync API)           |

---

## 📁 Project Structure

```bash
timebox-python/
│
├── app/                        # FastAPI backend
│   ├── main.py
│   ├── routes/
│   └── templates/
│
├── tests/                      # Test suite
│   ├── test_api.py             # API tests
│   ├── test_ui_playwright.py   # UI tests
│
├── demo_browser_run.py         # Full automated demo
├── demo_screenshots/           # Captured screenshots
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone (https://github.com/hamizs/TimeBox)
cd timebox-python
```

### 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers

```bash
python -m playwright install
```

---

## ▶️ Running the Application

```bash
uvicorn app.main:app --reload
```

Open:

```
http://127.0.0.1:8000
```

---

## 🧪 Running Tests

### API Tests

```bash
PYTHONPATH=. pytest tests/test_api.py -v
```

### UI Tests (Playwright)

```bash
uvicorn app.main:app --reload
PYTHONPATH=. pytest tests/test_ui_playwright.py -v
```

### Run All Tests

```bash
PYTHONPATH=. pytest -v
```

---

## 🎯 Features Tested

* ✅ User registration & authentication
* ✅ Task creation, editing, deletion
* ✅ Task completion & status toggling
* ✅ Filtering (All, Active, Completed, Overdue)
* ✅ Sorting (date, title)
* ✅ Search functionality
* ✅ Dashboard metrics
* ✅ Async loading behavior

---

## ⚠️ Flakiness Simulation (Core Concept)

This project intentionally includes real-world instability factors:

| Scenario            | Description                              |
| ------------------- | ---------------------------------------- |
| Time-based logic    | Tasks change status based on system time |
| Async UI delays     | Simulated loading states                 |
| Ordering issues     | Tasks with similar timestamps            |
| Race conditions     | Rapid user interactions                  |
| Network variability | Delayed responses                        |

---

## 📊 Testing Strategy

### API Testing

* FastAPI `TestClient`
* Validates business logic and endpoints
* Independent of UI

### UI Testing

* Playwright (Chromium)
* Simulates real user behavior
* Validates full user workflows

### Demo Automation

* Runs full test flow visually
* Ideal for presentations
* Demonstrates real-time test execution

---

## 🧠 Key Learnings

* Importance of **stable selectors over time-based waits**
* Handling **async rendering in UI tests**
* Managing **test isolation and data reset**
* Avoiding **flaky tests caused by timing dependencies**
* Designing tests for **real-world conditions, not ideal environments**

---

## 🐛 Troubleshooting

### Playwright not installed

```bash
pip install playwright
python -m playwright install
```

### Wrong Python interpreter (VS Code)

Select:

```
.venv/bin/python
```

### Import error (`No module named app`)

```bash
export PYTHONPATH=.
```

### Port already in use

```bash
lsof -i :8000
kill -9 <PID>
```

---

## 💡 Future Improvements

* Add Docker support
* CI/CD pipeline with GitHub Actions
* Cross-browser testing (Firefox/WebKit)
* Performance/load testing integration
* Visual regression testing

---

## 👤 Author

**Hamiz Siddiqui**
Software Engineering / IT Support / QA Enthusiast

---

## ⭐ Project Purpose

This project was built to demonstrate:

* Real-world software testing scenarios
* Automated UI testing with Playwright
* Detection and mitigation of flaky tests
* End-to-end test visibility through browser automation

---

## 📌 How to Showcase This Project

For best results:

1. Run `demo_browser_run.py`
2. Record your screen
3. Show browser executing tests live
4. Explain flakiness concepts

---
