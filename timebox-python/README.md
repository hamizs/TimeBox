# TimeBox – Python Software Testing Project

## Overview

TimeBox is a **task reminder web application** built with FastAPI and tested using Pytest and Playwright.

This project demonstrates:

* Functional testing (API + UI)
* End-to-end browser automation
* Test flakiness concepts (timing, async behavior, UI delays)
* Automated demo execution with visible browser interaction

---

## Tech Stack

* **Backend:** FastAPI
* **Frontend:** Jinja Templates + HTML/CSS/JS
* **Database:** SQLite
* **Testing:** Pytest + Playwright (Python)

---

## Project Structure

```
timebox-python/
│
├── app/                    # FastAPI application
├── tests/                  # API and UI tests
│   ├── test_api.py
│   ├── test_ui_playwright.py
│
├── demo_browser_run.py     # Full automated browser demo
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## Setup (Mac / VS Code)

### 1. Create virtual environment

```
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Install Playwright browsers

```
python -m playwright install
```

---

## Running the Application

Start the FastAPI server:

```
uvicorn app.main:app --reload
```

Open in browser:

```
http://127.0.0.1:8000
```

---

## Running Tests

### API Tests

```
PYTHONPATH=. pytest tests/test_api.py -v
```

### UI Tests (Playwright)

Make sure the server is running:

```
uvicorn app.main:app --reload
```

Then run:

```
PYTHONPATH=. pytest tests/test_ui_playwright.py -v
```

### Run All Tests

```
PYTHONPATH=. pytest -v
```

---

## Demo Script (Recommended for Presentation)

This project includes a **full automated demo script** that:

* Starts the backend automatically
* Opens a real browser
* Performs all user actions step-by-step
* Shows interactions visually
* Runs each test sequentially
* Prints PASS/FAIL results
* Takes screenshots

### Run Demo

```
python demo_browser_run.py
```

### Important Notes

* Do NOT run `uvicorn` manually when using the demo script
* The script will:

  * reset database
  * start server
  * run all browser tests
  * shut down automatically

---

## Features Tested

* User registration
* User login/logout
* Create tasks
* Edit tasks
* Delete tasks
* Mark complete / active
* Search tasks
* Filter tasks
* Sort tasks
* Dashboard counts
* Loading delays (flakiness simulation)

---

## Flakiness Concepts Demonstrated

This project intentionally includes real-world testing challenges:

* Time-based logic (due today vs overdue)
* Async UI loading delays
* Dynamic ordering of data
* Network timing variations
* UI rendering delays

These help demonstrate:

* Stable vs flaky test behavior
* Importance of proper waits/selectors
* Real-world testing conditions

---

## Troubleshooting

### Playwright not found

```
pip install playwright
python -m playwright install
```

### Wrong Python interpreter

Make sure VS Code uses:

```
.venv/bin/python
```

### ModuleNotFoundError: app

```
export PYTHONPATH=.
```

### Address already in use

Kill running server:

```
lsof -i :8000
kill -9 <PID>
```

---

## Author

TimeBox Testing Project – Built for demonstrating software testing concepts using Python and Playwright.

---
