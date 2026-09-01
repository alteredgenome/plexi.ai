<div align="center">

# Plexi (plexi.ai / plexi.fyi)

**Open-Source, Self-Hosted AI Executive Assistant & Dynamic Daily Planner**

*Inspired by Motion, Reclaim AI, Monday, and Saner AI.*

[![License: MIT](https://img.shields.io/badge/License-MIT-indigo.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![WebSockets](https://img.shields.io/badge/WebSockets-Voice%20Ready-violet.svg)]()

</div>

---

## ⚡ Quick Install (One-Liner)

Install Plexi and all dependencies to `/opt/plexi` with a single command:

```bash
curl -fsSL https://plexi.fyi/install.sh | bash
```

Once installed, open `http://<your-server-ip>:8000` (or `http://localhost:8000`) in your browser to launch Plexi's streamlined **First-Run Setup Wizard**.

---

## ✨ Features

- 🧠 **Dynamic Time & Buffer Engine:** Auto-schedules tasks around fixed meetings while enforcing pre-event travel buffers and post-event mental recovery windows.
- 📅 **Calendar Sync & Import:** Subscribe to live **Google Calendar** and **Microsoft Outlook** iCal feeds, or upload standard `.ics` calendar files.
- 🛡️ **Habit Defense:** Protects focus sprints and daily routines with flexible, protected, or locked defense strictness.
- 🔋 **Biohacking Readiness (RingConn Gen 2 Air):** Ingests sleep score and HRV to dynamically scale daily workload capacity ($60\% \to 115\%$).
- ⚡ **Pavlok 3 Haptic Momentum:** Optional haptic vibration, beeps, or gentle reminders when critical momentum tasks are overdue.
- 🏠 **Home Assistant Integration:** Synchronizes lighting scenes (Focus Time, Meeting Mode, Wind Down) and powers Home Assistant Voice / Assist.
- 💸 **Household Finance & Shared Utilities:** Ledger with debt simplification matrix to clear balances among roommates/partners with minimal transactions.
- 🔒 **Privacy Masking:** Privacy controls displaying sensitive personal calendar items as `"Busy"` for household views.

---

## 🚀 Manual Quickstart

```bash
git clone https://github.com/alteredgenome/plexi.ai.git /opt/plexi
cd /opt/plexi

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🐳 Docker Deployment

```bash
docker-compose up -d --build
```

---

## 🧪 Testing

```bash
pytest -v
```

---

## 📄 License

MIT License. Designed for privacy-first, self-hosted productivity.
