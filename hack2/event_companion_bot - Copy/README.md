# 🤖 Event Companion Bot
### TechFest 2025 — Interactive Telegram-style Event Assistant

A fully functional **Telegram-style Event Companion Bot** built with **Python + Flask** (backend) and **HTML + CSS + JavaScript** (frontend).

---

## 📁 Project Structure

```
event_companion_bot/
├── app.py              ← Flask web server & API endpoints
├── bot.py              ← Bot logic: FAQ engine, registration, feedback
├── data.json           ← Event data: schedule, venue, rules, prizes, FAQs
├── requirements.txt    ← Python dependencies
├── event_data.db       ← Auto-created SQLite database
│
├── templates/
│   └── index.html      ← Telegram-style chat UI
│
├── static/
│   ├── style.css       ← All styles + animations
│   └── script.js       ← All interactive JavaScript
│
└── README.md
```

---

## ⚙️ Installation & Setup

### 1. Install Python dependencies

Open a terminal in the `event_companion_bot/` folder and run:

```bash
pip install -r requirements.txt
```

### 2. Start the Flask server

```bash
python app.py
```

You should see:

```
✅  Event Companion Bot running at  http://127.0.0.1:5000
```

### 3. Open in Chrome

Navigate to:

```
http://127.0.0.1:5000
```

---

## 🌟 Features

| Feature | Description |
|---|---|
| 💬 **Telegram-style UI** | Dark-themed chat interface with avatars, bubbles, typing animation |
| 📝 **Event Registration** | Form → stored in SQLite → unique `EC-XXXX` ID returned |
| 📅 **Schedule** | Animated slide-in schedule cards |
| 📍 **Venue** | Address + Google Maps button |
| 📜 **Rules** | Animated rule list |
| 🏆 **Prizes** | Animated gold/silver/bronze prize cards |
| ⏰ **Countdown Timer** | Live JavaScript countdown to AI Workshop (auto-notifies at zero) |
| ❓ **FAQ Engine** | Keyword-based FAQ matching via Python |
| ⭐ **Feedback** | 5-star rating + text → stored in SQLite |
| 🔔 **Notifications** | Animated toast notification when countdown reaches zero |

---

## 🔗 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/event` | Returns all event data (schedule, venue, rules, prizes, FAQs) |
| POST | `/api/register` | Register a participant — returns `reg_id` |
| POST | `/api/faq` | Answer a question using the bot's FAQ engine |
| POST | `/api/feedback` | Save a star rating + feedback message |

---

## 💡 Notes

- The SQLite database (`event_data.db`) is created automatically on first run.
- The countdown timer targets 11:00 AM today (AI Workshop). If that time has already passed today, it targets 11:00 AM tomorrow for demo purposes.
- To customise event details, edit `data.json` — no code changes needed.
- Tested on **Google Chrome** (recommended).
