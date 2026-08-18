"""
app.py - Flask web backend for Event Companion Bot
"""

from flask import Flask, render_template, request, jsonify
import bot

app = Flask(__name__)

# ─── Main Pages ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/registration")
def page_registration():
    return render_template("registration.html")

@app.route("/schedule")
def page_schedule():
    data = bot.get_event_info()
    return render_template("schedule.html", schedule=data["schedule"])

@app.route("/venue")
def page_venue():
    data = bot.get_event_info()
    return render_template("venue.html", venue=data["venue"])

@app.route("/rules")
def page_rules():
    data = bot.get_event_info()
    return render_template("rules.html", rules=data["rules"])

@app.route("/prizes")
def page_prizes():
    data = bot.get_event_info()
    return render_template("prizes.html", prizes=data["prizes"])

@app.route("/reminders")
def page_reminders():
    return render_template("reminders.html")

@app.route("/faq")
def page_faq():
    return render_template("faq.html")

@app.route("/feedback")
def page_feedback():
    return render_template("feedback.html")

@app.route("/help")
def page_help():
    data = bot.get_event_info()
    return render_template("help.html", help=data["help"])

@app.route("/attendance")
def page_attendance():
    students = bot.get_all_students()
    total    = len(students)
    present  = sum(1 for s in students if s["present"] == 1)
    return render_template("attendance.html", students=students, total=total, present=present, absent=total-present)

# ─── API: Event data ─────────────────────────────────────────────────────────

@app.route("/api/event", methods=["GET"])
def api_event():
    data = bot.get_event_info()
    return jsonify({"status": "ok", "data": data})

# ─── API: Registration ────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def api_register():
    body      = request.get_json(force=True) or {}
    name      = body.get("name",      "").strip()
    email     = body.get("email",     "").strip()
    phone     = body.get("phone",     "").strip()
    college   = body.get("college",   "").strip()
    roll_no   = body.get("roll_no",   "-").strip()
    team_id   = body.get("team_id",   "-").strip()
    team_name = body.get("team_name", "-").strip()
    team_type = body.get("team_type", "-").strip()

    if not all([name, email, phone, college]):
        return jsonify({"status": "error", "message": "All fields are required."}), 400
    if "@" not in email or "." not in email:
        return jsonify({"status": "error", "message": "Please enter a valid email address."}), 400

    reg_id = bot.register_participant(name, email, phone, college, roll_no, team_id, team_name, team_type)
    return jsonify({"status": "ok", "reg_id": reg_id})

# ─── API: Medical Helpline ────────────────────────────────────────────────────

@app.route("/api/medical", methods=["GET"])
def api_medical():
    data = bot.get_event_info()
    return jsonify({"status": "ok", "data": data.get("medical", {})})

# ─── API: FAQ ─────────────────────────────────────────────────────────────────

@app.route("/api/faq", methods=["POST"])
def api_faq():
    body  = request.get_json(force=True) or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Please enter a question."}), 400
    answer = bot.answer_faq(query)
    return jsonify({"status": "ok", "answer": answer})

# ─── API: Attendance ─────────────────────────────────────────────────────────

@app.route("/api/attendance/mark", methods=["POST"])
def api_mark_attendance():
    body = request.get_json(force=True) or {}
    att_id = body.get("attendance_id", "").strip().upper()
    action = body.get("action", "present")   # "present" or "absent"
    if not att_id:
        return jsonify({"status": "error", "message": "Attendance ID required."}), 400
    student = bot.get_student_by_id(att_id)
    if not student:
        return jsonify({"status": "error", "message": f"No student found with ID {att_id}"}), 404
    if action == "present":
        bot.mark_present(att_id)
    else:
        bot.mark_absent(att_id)
    return jsonify({"status": "ok", "student": student["name"], "action": action})

@app.route("/api/attendance/search", methods=["GET"])
def api_search_student():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"status": "error", "message": "Query required."}), 400
    students = bot.get_all_students()
    q_lower  = q.lower()
    results  = [s for s in students if q_lower in s["name"].lower() or q_lower in s["attendance_id"].lower() or q_lower in s["phone"]]
    return jsonify({"status": "ok", "results": results})

# ─── API: Feedback ────────────────────────────────────────────────────────────

@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    body    = request.get_json(force=True) or {}
    rating  = body.get("rating")
    message = body.get("message", "").strip()
    if rating is None or not (1 <= int(rating) <= 5):
        return jsonify({"status": "error", "message": "Please select a rating between 1 and 5."}), 400
    bot.save_feedback(rating, message)
    return jsonify({"status": "ok", "message": "Thank you for your feedback!"})

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("✅  Event Companion Bot running at  http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
