"""
bot.py – Event Companion Bot logic
Handles FAQ matching, registration, attendance, and feedback storage.
"""

import json
import os
import re
import uuid
import sqlite3
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
DB_FILE   = os.path.join(os.path.dirname(__file__), "event_data.db")


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Database setup ───────────────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS registrations (
            attendance_id   TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            email           TEXT NOT NULL,
            phone           TEXT NOT NULL,
            college         TEXT NOT NULL,
            present         INTEGER DEFAULT 0,
            registered_at   TEXT NOT NULL,
            roll_no         TEXT DEFAULT '-',
            team_id         TEXT DEFAULT '-',
            team_name       TEXT DEFAULT '-',
            team_type       TEXT DEFAULT '-'
        )
    """)
    # Add columns for upgrading from old DB
    for col, default in [
        ("present",   "INTEGER DEFAULT 0"),
        ("roll_no",   "TEXT DEFAULT '-'"),
        ("team_id",   "TEXT DEFAULT '-'"),
        ("team_name", "TEXT DEFAULT '-'"),
        ("team_type", "TEXT DEFAULT '-'"),
    ]:
        try:
            c.execute(f"ALTER TABLE registrations ADD COLUMN {col} {default}")
        except Exception:
            pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            rating       INTEGER NOT NULL,
            message      TEXT,
            submitted_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS team_marks (
            team_id      INTEGER PRIMARY KEY,
            marks        REAL    DEFAULT 0,
            remarks      TEXT    DEFAULT '',
            updated_at   TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ─── Registration ─────────────────────────────────────────────────────────────

def register_participant(name, email, phone, college, roll_no="-", team_id="-", team_name="-", team_type="-"):
    """Save a new registration. Returns the generated ATT-XXXX attendance id."""
    conn = sqlite3.connect(DB_FILE)
    c    = conn.cursor()
    c.execute("SELECT COUNT(*) FROM registrations")
    count  = c.fetchone()[0]
    att_id = f"ATT-{str(count + 1).zfill(4)}"
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """INSERT INTO registrations
           (attendance_id, name, email, phone, college, present, registered_at,
            roll_no, team_id, team_name, team_type)
           VALUES (?,?,?,?,?,0,?,?,?,?,?)""",
        (att_id, name.strip(), email.strip(), phone.strip(), college.strip(), now,
         str(roll_no).strip(), str(team_id).strip(), str(team_name).strip(), str(team_type).strip())
    )
    conn.commit()
    conn.close()
    return att_id


# ─── Attendance ───────────────────────────────────────────────────────────────

def get_all_students():
    """Return all registered students as list of dicts."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c    = conn.cursor()
    c.execute("SELECT * FROM registrations ORDER BY registered_at DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def mark_present(attendance_id):
    """Mark a student as present. Returns True if found."""
    conn = sqlite3.connect(DB_FILE)
    c    = conn.cursor()
    c.execute("UPDATE registrations SET present=1 WHERE attendance_id=?", (attendance_id,))
    updated = c.rowcount
    conn.commit()
    conn.close()
    return updated > 0

def mark_absent(attendance_id):
    """Mark a student as absent."""
    conn = sqlite3.connect(DB_FILE)
    c    = conn.cursor()
    c.execute("UPDATE registrations SET present=0 WHERE attendance_id=?", (attendance_id,))
    conn.commit()
    conn.close()

def get_student_by_id(attendance_id):
    """Get a single student by attendance ID."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c    = conn.cursor()
    c.execute("SELECT * FROM registrations WHERE attendance_id=?", (attendance_id,))
    row  = c.fetchone()
    conn.close()
    return dict(row) if row else None


# ─── Language detection ───────────────────────────────────────────────────────

# Unicode block ranges for each script
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")   # Hindi + Marathi share Devanagari
_MALAYALAM  = re.compile(r"[\u0D00-\u0D7F]")
_GUJARATI   = re.compile(r"[\u0A80-\u0AFF]")
_GURMUKHI   = re.compile(r"[\u0A00-\u0A7F]")   # Punjabi (Gurmukhi script)
_TELUGU     = re.compile(r"[\u0C00-\u0C7F]")   # Telugu

# Marathi-specific common words to distinguish from Hindi
_MARATHI_WORDS = re.compile(
    r"(आहे|आहेत|आहो|नाही|मला|तुम्ही|करा|सांगा|कुठे|केव्हा|कसे|आणि|किंवा|येथे|रोजी|पर्यंत|मोफत|वेळापत्रक|बक्षिसे)"
)

# ── Hinglish / Romanized detection ───────────────────────────────────────────
# User types in Roman script but language is Hindi/Marathi/Gujarati/Punjabi
# Each tuple: (regex_pattern, language_code)
_HINGLISH_PATTERNS = [
    # Marathi Romanized — check before Hindi (more specific words)
    (re.compile(
        r"\b(kuthe|ithe|kasa|kashi|kaay|kay|aahe|nahi|mala|tumhi|kara|sanga|"
        r"kevha|aani|kinva|yethe|modat|baksheesh|velapatra|mahiti|sangto|"
        r"paise|jevna|utara|kiti|tumi)\b", re.I),
     "mr"),
    # Hindi Romanized
    (re.compile(
        r"\b(kahan|kab|kaise|kya|karo|batao|hai|hain|mujhe|mera|meri|"
        r"yahan|wahan|samay|niyam|puraskar|inaam|register|panjeekar|"
        r"madad|sahayata|sampark|khana|bhojan|taareekh|din|jagah|sthan|"
        r"paisa|trophy|certificate|puri|poori|kuch|aur|iska|uska)\b", re.I),
     "hi"),
    # Gujarati Romanized
    (re.compile(
        r"\b(kyaan|kya|shu|chhe|mane|tame|kem|kai|karo|javab|"
        r"mahiti|samay|niyam|inaam|nodhni|mafat|sthal|tarikha)\b", re.I),
     "gu"),
    # Punjabi Romanized
    (re.compile(
        r"\b(kithe|kiddan|kiven|kado|ki|haan|nahi|menu|tenu|"
        r"samaan|niyam|inaam|registration|mufat|thaan|taareekh)\b", re.I),
     "pa"),
]

def _detect_lang(text):
    """Detect language from Unicode script OR Romanized (Hinglish) patterns."""
    # ── Unicode script detection (highest priority) ──
    if _GURMUKHI.search(text):
        return "pa"
    if _TELUGU.search(text):
        return "te"
    if _GUJARATI.search(text):
        return "gu"
    if _MALAYALAM.search(text):
        return "ml"
    if _DEVANAGARI.search(text):
        if _MARATHI_WORDS.search(text):
            return "mr"
        return "hi"
    # ── Romanized / Hinglish fallback ────────────────
    for pattern, lang in _HINGLISH_PATTERNS:
        if pattern.search(text):
            return lang
    return None   # pure English


# ─── Topic keyword map (all 6 languages per topic) ───────────────────────────

_TOPIC_MAP = [
    # venue
    (["venue","where","location","place","hall","seminar","lab","address","find",
      "कहाँ","कहां","जगह","स्थान","पता","हॉल",                     # Hindi
      "कुठे","ठिकाण","जागा",                                         # Marathi
      "\u0a95\u0acd\u0aaf\u0abe\u0a82","\u0ab8\u0acd\u0aa5\u0ab3",  # Gujarati ક્યાં,સ્થળ
      "\u0d0e\u0d35\u0d3f\u0d1f\u0d46","\u0d38\u0d4d\u0d25\u0d32\u0d02",  # Malayalam എവിടെ,സ്ഥലം
      "\u0a15\u0a3f\u0a71\u0a25\u0a47","\u0a1c\u0a17\u0a4d\u0a39\u0a3e",  # Punjabi ਕਿੱਥੇ,ਜਗ੍ਹਾ
      "\u0c0e\u0c15\u0c4d\u0c15\u0c21","\u0c38\u0c4d\u0c25\u0c32\u0c02"],  # Telugu ఎక్కడ,స్థలం
     "venue"),

    # schedule / time
    (["schedule","time","timing","timetable","agenda","program","session",
      "समय","कार्यक्रम","टाइम","कब","कितने","बजे","शेड्यूल",        # Hindi
      "वेळापत्रक","वेळ","केव्हा",                                     # Marathi
      "\u0ab8\u0aae\u0aaf","\u0a95\u0abe\u0ab0\u0acd\u0aaf\u0a95\u0acd\u0ab0\u0aae",  # Gujarati સમय,કાર્યક્રम
      "\u0d37\u0d46\u0d21\u0d4d\u0d2f\u0d42\u0d7e","\u0d38\u0d2e\u0d2f\u0d02",       # Malayalam ഷെഡ്യൂൾ,സമയം
      "\u0a38\u0a2e\u0a3e\u0a02","\u0a38\u0a2e\u0a47\u0a02",         # Punjabi ਸਮਾਂ,ਸਮੇਂ
      "\u0c38\u0c2e\u0c2f\u0c02","\u0c37\u0c46\u0c21\u0c4d\u0c2f\u0c42\u0c32\u0c4d"],  # Telugu సమయం,షెడ్యూల్
     "schedule"),

    # register
    (["register","registration","sign","enroll","signup","free","form","join",
      "रजिस्ट्रेशन","पंजीकरण","मुफ्त","मुफ़्त","भरें","दर्ज",       # Hindi
      "नोंदणी","मोफत","भरा",                                          # Marathi
      "\u0aa8\u0acb\u0a82\u0aa7\u0aa3\u0ac0","\u0aae\u0aab\u0aa4",  # Gujarati નોંધણી,મફત
      "\u0d30\u0d1c\u0d3f\u0d38\u0d4d\u0d1f\u0d4d\u0d30\u0d47\u0d37\u0d28\u0d4d","\u0d38\u0d57\u0d1c\u0d28\u0d4d\u0d2f\u0d02",  # Malayalam രജിസ്ട്രേഷൻ,സൗജന്യം
      "\u0a30\u0a1c\u0a3f\u0a38\u0a1f\u0a4d\u0a30\u0a47\u0a38\u0a3c\u0a28","\u0a2e\u0a41\u0a2b\u0a3c\u0a24",  # Punjabi ਰਜਿਸਟ੍ਰੇਸ਼ਨ,ਮੁਫ਼ਤ
      "\u0c28\u0c2e\u0c4b\u0c26\u0c41","\u0c09\u0c1a\u0c3f\u0c24\u0c02"],  # Telugu నమోదు,ఉచితం
     "register"),

    # prizes
    (["prize","prizes","award","reward","money","cash","trophy","certificate","medal","win",
      "पुरस्कार","इनाम","ट्रॉफी","सर्टिफिकेट","पैसे","जीत",         # Hindi
      "बक्षीस","बक्षिसे",                                             # Marathi
      "\u0aaa\u0ac1\u0ab0\u0ab8\u0acd\u0a95\u0abe\u0ab0","\u0a87\u0aa8\u0abe\u0aae",  # Gujarati પुरस्कार,ઇнаам
      "\u0d38\u0d2e\u0d4d\u0d2e\u0d3e\u0d28\u0d02","\u0d1f\u0d4d\u0d30\u0d4b\u0d2b\u0d3f",  # Malayalam സമ്മാനം,ട്രോഫി
      "\u0a07\u0a28\u0a3e\u0a2e","\u0a1f\u0a30\u0a3e\u0a2b\u0a40",  # Punjabi ਇਨਾਮ,ਟਰਾਫੀ
      "\u0c2c\u0c39\u0c41\u0c2e\u0c24\u0c3f","\u0c1f\u0c4d\u0c30\u0c4b\u0c2b\u0c40"],  # Telugu బహుమతి,ట్రోఫీ
     "prizes"),

    # rules
    (["rule","rules","guideline","regulation","conduct","discipline",
      "नियम","नियमावली","अनुशासन",                                    # Hindi
      "शिस्त",                                                         # Marathi
      "\u0aa8\u0abf\u0aaf\u0aae","\u0aa8\u0abf\u0aaf\u0aae\u0acb",  # Gujarati નિयम,નિयमो
      "\u0d28\u0d3f\u0d2f\u0d2e\u0d02","\u0d1a\u0d1f\u0d4d\u0d1f\u0d02",  # Malayalam നിয\u0d2eം,ചট്ടം
      "\u0a28\u0a3f\u0a2f\u0a2e",                                     # Punjabi ਨਿਯਮ
      "\u0c28\u0c3f\u0c2f\u0c2e\u0c3e\u0c32\u0c41","\u0c28\u0c3f\u0c2c\u0c02\u0c27\u0c28"],  # Telugu నియమాలు,నిబంధన
     "rules"),

    # date
    (["date","day","when","august","2026",
      "तारीख","दिन","कब","अगस्त",                                     # Hindi
      "दिवस","ऑगस्ट",                                                  # Marathi
      "\u0aa4\u0abe\u0ab0\u0ac0\u0a96","\u0aa6\u0abf\u0ab5\u0ab8",  # Gujarati તારีख,દివस
      "\u0d24\u0d40\u0d2f\u0d24\u0d3f","\u0d26\u0d3f\u0d35\u0d38\u0d02",  # Malayalam തീযതി,ദিवसം
      "\u0a24\u0a3e\u0a30\u0a40\u0a16","\u0a26\u0a3f\u0a28",         # Punjabi ਤਾਰੀਖ,ਦਿਨ
      "\u0c24\u0c47\u0c26\u0c40","\u0c30\u0c4b\u0c1c\u0c41"],        # Telugu తేదీ,రోజు
     "date"),

    # contact
    (["contact","coordinator","help","support","phone","call","sandhya","mam","number",
      "संपर्क","फोन","नंबर","मदद","सहायता",                           # Hindi
      # Marathi same as Hindi for contact
      "\u0ab8\u0a82\u0aaa\u0ab0\u0acd\u0a95","\u0aab\u0acb\u0aa8",  # Gujarati સংपर्क,ফোन
      "\u0d2c\u0d28\u0d4d\u0d27\u0d02","\u0d2b\u0d4b\u0d23\u0d4d",  # Malayalam ബന്ധം,ഫോൺ
      "\u0a38\u0a70\u0a2a\u0a30\u0a15","\u0a2b\u0a3c\u0a4b\u0a28",  # Punjabi ਸੰਪਰਕ,ਫ਼ੋਨ
      "\u0c38\u0c02\u0c2a\u0c4d\u0c30\u0c26\u0c3f\u0c02\u0c1a\u0c41","\u0c2b\u0c4b\u0c28\u0c4d"],  # Telugu సంప్రదించు,ఫోన్
     "contact"),

    # emergency
    (["emergency","urgent","ambulance","police","danger","accident","medical",
      "आपातकाल","एम्बुलेंस","पुलिस","खतरा","दुर्घटना",               # Hindi
      "आणीबाणी","रुग्णवाहिका",                                         # Marathi
      "\u0a95\u0a9f\u0acb\u0a95\u0a9f\u0ac0","\u0a8f\u0aae\u0acd\u0aac\u0acd\u0aaf\u0ac1\u0ab2\u0aa8\u0acd\u0ab8",  # Gujarati
      "\u0d05\u0d1f\u0d3f\u0d2f\u0d28\u0d4d\u0d24\u0d30\u0d02","\u0d06\u0d02\u0d2c\u0d41\u0d32\u0d7b\u0d38\u0d4d",  # Malayalam
      "\u0a10\u0a2e\u0a30\u0a1c\u0a48\u0a02\u0a38\u0a40","\u0a10\u0a02\u0a2c\u0a42\u0a32\u0a48\u0a02\u0a38",  # Punjabi
      "\u0c05\u0c24\u0c4d\u0c2f\u0c35\u0c38\u0c30\u0c02","\u0c05\u0c02\u0c2c\u0c41\u0c32\u0c46\u0c28\u0c4d\u0c38\u0c4d"],  # Telugu
     "emergency"),

    # food → schedule (lunch info is in schedule)
    (["food","lunch","meal","eat","snack",
      "खाना","भोजन","लंच","खाने",                                     # Hindi
      "जेवण","खाणे",                                                   # Marathi
      "\u0aad\u0acb\u0a9c\u0aa8","\u0a96\u0abe\u0ab5\u0abe\u0aa8\u0ac1\u0a82",  # Gujarati
      "\u0d2d\u0d15\u0d4d\u0d37\u0d23\u0d02","\u0d09\u0d1a\u0d4d\u0d1a\u0d2d\u0d15\u0d4d\u0d37\u0d23\u0d02",  # Malayalam
      "\u0a16\u0a3e\u0a23\u0a3e","\u0a2d\u0a4b\u0a1c\u0a28",         # Punjabi
      "\u0c2d\u0c4b\u0c1c\u0c28\u0c02","\u0c24\u0c3f\u0c28\u0c21\u0c02"],  # Telugu
     "schedule"),
]

def _match_topic(text):
    """Return the best-matching topic key — substring search in original text."""
    for keywords, topic in _TOPIC_MAP:
        for kw in keywords:
            if kw in text:
                return topic
    return None


# ─── FAQ matching ─────────────────────────────────────────────────────────────

def _tokenize(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def answer_faq(user_query):
    """Return the best-matching FAQ answer (multilingual-aware), or a fallback string."""
    data = load_data()
    lang = _detect_lang(user_query)

    # ── Non-English path ──────────────────────────────────────────
    if lang:
        ml_data = data.get("multilang", {}).get(lang, {})
        topic   = _match_topic(user_query)
        if topic and topic in ml_data:
            return ml_data[topic]
        # language detected but topic unknown → fallback in same language
        return ml_data.get("fallback",
            "I'm not sure about that. Please contact Miss. Sandhya Aghav Mam — 9579001895.")

    # ── English path (original keyword matching) ──────────────────
    faqs   = data["faqs"]
    tokens = _tokenize(user_query)

    best_score  = 0
    best_answer = None

    for faq in faqs:
        kw_tokens = _tokenize(" ".join(faq["keywords"]))
        score     = len(tokens & kw_tokens)
        if score > best_score:
            best_score  = score
            best_answer = faq["answer"]

    if best_score == 0:
        return (
            "I'm not sure about that. Please contact Miss. Sandhya Aghav Mam — 9579001895 "
            "or try asking about: venue, schedule, prizes, rules, registration, or workshop timings."
        )
    return best_answer


# ─── Feedback ─────────────────────────────────────────────────────────────────

def save_feedback(rating, message):
    """Persist user feedback to the database."""
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO feedback (rating, message, submitted_at) VALUES (?, ?, ?)",
        (int(rating), message.strip(), now)
    )
    conn.commit()
    conn.close()


# ─── Marks ────────────────────────────────────────────────────────────────────

def save_marks(team_id, marks, remarks=""):
    """Insert or update marks for a team."""
    now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        INSERT INTO team_marks (team_id, marks, remarks, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(team_id) DO UPDATE SET
            marks      = excluded.marks,
            remarks    = excluded.remarks,
            updated_at = excluded.updated_at
    """, (int(team_id), float(marks), remarks.strip(), now))
    conn.commit()
    conn.close()

def get_all_marks():
    """Return dict of {team_id: {marks, remarks, updated_at}}."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM team_marks").fetchall()
    conn.close()
    return {r["team_id"]: dict(r) for r in rows}


# ─── Event info helpers ───────────────────────────────────────────────────────

def get_event_info():
    return load_data()

def get_teams():
    """Return team seating allocation list from data.json."""
    return load_data().get("teams", [])


# ─── Init on import ───────────────────────────────────────────────────────────

init_db()
