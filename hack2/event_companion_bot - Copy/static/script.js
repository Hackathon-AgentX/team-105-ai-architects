/* ═══════════════════════════════════════════════════
   Event Companion Bot — script.js
alag alg tab nahi    Voice Input  : Web Speech API (SpeechRecognition)
   Voice Output : Web Speech API (SpeechSynthesis)
   ═══════════════════════════════════════════════════ */

"use strict";

// ── Global state ──────────────────────────────────────────────────
let eventData       = null;   // From /api/event
let countdownTarget = null;   // Date for countdown
let countdownTimer  = null;   // setInterval handle
let selectedRating  = 0;      // Star rating value
let voiceEnabled    = true;   // Bot speaks replies aloud
let recognition     = null;   // SpeechRecognition instance
let isListening     = false;  // Mic active flag

// ── DOM refs ──────────────────────────────────────────────────────
const msgArea        = document.getElementById("msgArea");
const userInput      = document.getElementById("userInput");
const sendBtn        = document.getElementById("sendBtn");
const typingRow      = document.getElementById("typingRow");
const micBtn         = document.getElementById("micBtn");
const voiceToggleBtn = document.getElementById("voiceToggleBtn");
const voiceOverlay   = document.getElementById("voiceOverlay");
const voiceStatus    = document.getElementById("voiceStatus");
const voiceTranscript= document.getElementById("voiceTranscript");
const voiceCancel    = document.getElementById("voiceCancel");

// ═════════════════════════════════════════════════════════════════
// Helpers
// ═════════════════════════════════════════════════════════════════

function pad2(n) { return String(n).padStart(2, "0"); }

function nowTime() {
  const d = new Date();
  let h = d.getHours(), m = d.getMinutes();
  return `${pad2(h % 12 || 12)}:${pad2(m)} ${h < 12 ? "AM" : "PM"}`;
}

function scrollBottom() {
  msgArea.scrollTop = msgArea.scrollHeight;
}

/** Strip HTML tags for plain-text TTS */
function stripHtml(html) {
  const tmp = document.createElement("div");
  tmp.innerHTML = html;
  return tmp.textContent || tmp.innerText || "";
}

// ═════════════════════════════════════════════════════════════════
// Voice OUTPUT — Text-to-Speech (bot speaks replies)
// ═════════════════════════════════════════════════════════════════

function speak(text) {
  if (!voiceEnabled) return;
  if (!window.speechSynthesis) return;

  // Cancel any ongoing speech first
  window.speechSynthesis.cancel();

  const plain   = stripHtml(text).replace(/[🤖📝📅📍📜🏆⏰❓⭐✅💙🎉💻🍽️]/gu, "");
  const utt     = new SpeechSynthesisUtterance(plain);
  utt.lang      = "en-IN";   // Indian English accent
  utt.rate      = 0.95;
  utt.pitch     = 1.05;
  utt.volume    = 1.0;

  // Pick a natural voice if available
  const voices  = window.speechSynthesis.getVoices();
  const preferred = voices.find(v =>
    v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural"))
  ) || voices.find(v => v.lang.startsWith("en"));
  if (preferred) utt.voice = preferred;

  window.speechSynthesis.speak(utt);
}

// Voices load asynchronously on some browsers
window.speechSynthesis && window.speechSynthesis.addEventListener("voiceschanged", () => {});

// ═════════════════════════════════════════════════════════════════
// Voice INPUT — Speech-to-Text (user speaks, bot hears)
// ═════════════════════════════════════════════════════════════════

function initSpeechRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    micBtn.title = "Voice input not supported in this browser";
    micBtn.style.opacity = "0.4";
    micBtn.disabled = true;
    return;
  }

  recognition             = new SR();
  recognition.lang        = "en-IN";
  recognition.interimResults = true;   // Show live transcript as user speaks
  recognition.maxAlternatives = 1;
  recognition.continuous  = false;

  recognition.onstart = () => {
    isListening = true;
    micBtn.classList.add("listening");
    voiceOverlay.style.display = "flex";
    voiceStatus.textContent    = "Listening… speak now";
    voiceTranscript.textContent = "";
  };

  recognition.onresult = (e) => {
    let interim = "", final = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) final += t;
      else interim += t;
    }
    voiceTranscript.textContent = final || interim;
    if (final) userInput.value = final;
  };

  recognition.onerror = (e) => {
    stopListening();
    if (e.error === "not-allowed" || e.error === "permission-denied") {
      alert("Microphone access denied. Please allow mic permission in Chrome and try again.");
    } else if (e.error !== "aborted") {
      showVoiceError("Could not hear you. Please try again.");
    }
  };

  recognition.onend = () => {
    stopListening();
    const spoken = userInput.value.trim();
    if (spoken) {
      // Auto-send after a short pause
      setTimeout(() => handleUserMessage(), 300);
    }
  };
}

function startListening() {
  if (!recognition) return;
  if (isListening) { stopListening(); return; }
  try { recognition.start(); }
  catch (e) { /* already running */ }
}

function stopListening() {
  isListening = false;
  micBtn.classList.remove("listening");
  voiceOverlay.style.display = "none";
  voiceStatus.textContent    = "Listening…";
  voiceTranscript.textContent = "";
  try { recognition && recognition.abort(); } catch (e) {}
}

function showVoiceError(msg) {
  voiceStatus.textContent    = "⚠️ " + msg;
  voiceStatus.style.color    = "#e74c3c";
  setTimeout(() => {
    stopListening();
    voiceStatus.style.color = "";
  }, 2000);
}

// Mic button click
micBtn.addEventListener("click", () => {
  if (isListening) stopListening();
  else startListening();
});

// Cancel button inside overlay
voiceCancel.addEventListener("click", stopListening);

// ── Voice output toggle ────────────────────────────────────────
voiceToggleBtn.addEventListener("click", () => {
  voiceEnabled = !voiceEnabled;
  window.speechSynthesis && window.speechSynthesis.cancel();
  voiceToggleBtn.textContent = voiceEnabled ? "🔊" : "🔇";
  voiceToggleBtn.classList.toggle("muted", !voiceEnabled);
  voiceToggleBtn.title = voiceEnabled ? "Bot voice on" : "Bot voice off";

  // Tiny confirmation message
  addMessage(
    voiceEnabled
      ? "🔊 <strong>Voice ON</strong> — I will now speak my replies aloud."
      : "🔇 <strong>Voice OFF</strong> — Replies will be text-only.",
    "bot"
  );
});

// ═════════════════════════════════════════════════════════════════
// Message rendering
// ═════════════════════════════════════════════════════════════════

function addMessage(text, who = "bot", buttons = []) {
  const wrap   = document.createElement("div");
  wrap.className = `msg ${who}`;

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML = text;

  const time   = document.createElement("span");
  time.className = "msg-time";
  time.textContent = nowTime();

  wrap.appendChild(bubble);

  if (buttons.length) {
    const btnRow = document.createElement("div");
    btnRow.className = "msg-buttons";
    buttons.forEach(b => {
      const btn = document.createElement("button");
      btn.type = "button";                        // ✅ prevent any form submit
      btn.className = "msg-btn";
      btn.textContent = b.label;
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        b.action();
      });
      btnRow.appendChild(btn);
    });
    wrap.appendChild(btnRow);
  }

  wrap.appendChild(time);
  msgArea.appendChild(wrap);
  scrollBottom();
}

function showTyping()  { typingRow.style.display = "flex"; scrollBottom(); }
function hideTyping()  { typingRow.style.display = "none"; }

/**
 * Bot typing animation → then reply (also speaks it).
 */
function botReply(html, buttons = [], delay = 900) {
  showTyping();
  setTimeout(() => {
    hideTyping();
    addMessage(html, "bot", buttons);
    speak(html);            // 🔊 speak the reply
  }, delay);
}

// ═════════════════════════════════════════════════════════════════
// Modals
// ═════════════════════════════════════════════════════════════════

function openModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  // Remove any leftover inline display, force open via class + inline style together
  el.style.cssText = "display:flex !important;";
  el.classList.add("open");
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("open");
  el.style.cssText = "display:none !important;";
}

document.querySelectorAll(".modal-close").forEach(btn => {
  btn.type = "button";
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    closeModal(btn.dataset.close);
  });
});
document.querySelectorAll(".modal-overlay").forEach(overlay => {
  overlay.addEventListener("click", e => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

// ═════════════════════════════════════════════════════════════════
// Load event data from Python backend
// ═════════════════════════════════════════════════════════════════

async function loadEventData() {
  try {
    const res  = await fetch("/api/event");
    const json = await res.json();
    eventData  = json.data;
    buildScheduleList();
    buildVenueCard();
    buildRulesList();
    buildPrizesGrid();
    initCountdown();
  } catch (err) {
    console.error("Could not load event data:", err);
  }
}

// ═════════════════════════════════════════════════════════════════
// Schedule / Venue / Rules / Prizes builders
// ═════════════════════════════════════════════════════════════════

function buildScheduleList() {
  const list = document.getElementById("scheduleList");
  list.innerHTML = "";
  eventData.schedule.forEach((item, i) => {
    const li = document.createElement("li");
    li.className = "schedule-item";
    li.style.animationDelay = `${i * 0.08}s`;
    li.innerHTML = `
      <span class="sched-icon">${item.icon}</span>
      <span class="sched-time">${item.time}</span>
      <span class="sched-title">${item.title}</span>`;
    list.appendChild(li);
  });
}

function buildVenueCard() {
  const v = eventData.venue;
  document.getElementById("venueCard").innerHTML = `
    <p><strong>${v.college}</strong></p>
    <p>${v.hall}</p>
    <p style="margin-top:6px;font-size:13px;color:var(--tg-muted)">${v.address}</p>
    <a class="venue-btn" href="${v.maps_url}" target="_blank" rel="noopener">📍 View Location</a>`;
}

function buildRulesList() {
  const ol = document.getElementById("rulesList");
  ol.innerHTML = "";
  eventData.rules.forEach((rule, i) => {
    const li = document.createElement("li");
    li.textContent = rule;
    li.style.animationDelay = `${i * 0.07}s`;
    ol.appendChild(li);
  });
}

function buildPrizesGrid() {
  const grid = document.getElementById("prizesGrid");
  grid.innerHTML = "";
  eventData.prizes.forEach(p => {
    const card = document.createElement("div");
    card.className = "prize-card";
    card.innerHTML = `
      <span class="prize-medal">${p.medal}</span>
      <div class="prize-rank">${p.rank} Prize</div>
      <div class="prize-amount">${p.amount}</div>`;
    grid.appendChild(card);
  });
}

// ═════════════════════════════════════════════════════════════════
// Countdown timer
// ═════════════════════════════════════════════════════════════════

function initCountdown() {
  const today  = new Date();
  const target = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 11, 0, 0);
  if (target <= today) target.setDate(target.getDate() + 1);
  countdownTarget = target;
  if (countdownTimer) clearInterval(countdownTimer);
  countdownTimer = setInterval(tickCountdown, 1000);
  tickCountdown();
}

function tickCountdown() {
  const now  = new Date();
  let   diff = Math.max(0, Math.floor((countdownTarget - now) / 1000));
  const h = Math.floor(diff / 3600); diff -= h * 3600;
  const m = Math.floor(diff / 60);   diff -= m * 60;
  const s = diff;

  function flip(el, val) {
    if (el && el.textContent !== pad2(val)) {
      el.style.transform = "scale(1.3)";
      el.textContent = pad2(val);
      setTimeout(() => el.style.transform = "", 150);
    }
  }
  flip(document.getElementById("cdH"), h);
  flip(document.getElementById("cdM"), m);
  flip(document.getElementById("cdS"), s);

  if (h === 0 && m === 0 && s === 0) {
    clearInterval(countdownTimer);
    showNotification("The AI Workshop is starting now!");
    speak("Attention! The AI Workshop is starting now. Please head to the seminar hall.");
  }
}

// ═════════════════════════════════════════════════════════════════
// Notification toast
// ═════════════════════════════════════════════════════════════════

function showNotification(text, duration = 5500) {
  const toast = document.getElementById("notifToast");
  document.getElementById("notifText").textContent = text;
  toast.style.display = "flex";
  setTimeout(() => { toast.style.display = "none"; }, duration);
}

// ═════════════════════════════════════════════════════════════════
// Registration
// ═════════════════════════════════════════════════════════════════

document.getElementById("regForm").addEventListener("submit", async e => {
  e.preventDefault();
  const name    = document.getElementById("regName").value.trim();
  const email   = document.getElementById("regEmail").value.trim();
  const phone   = document.getElementById("regPhone").value.trim();
  const college = document.getElementById("regCollege").value.trim();

  try {
    const res  = await fetch("/api/register", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, phone, college })
    });
    const json = await res.json();

    if (json.status === "ok") {
      document.getElementById("regForm").style.display    = "none";
      document.getElementById("regSuccess").style.display = "block";
      document.getElementById("regSuccessMsg").innerHTML  =
        `Registration Successful!<br>Welcome, <strong>${name}</strong>!<br>` +
        `Your Registration ID:<br>` +
        `<strong style="font-size:22px;color:var(--tg-accent)">${json.reg_id}</strong>`;

      botReply(
        `✅ <strong>Registration Successful!</strong><br>` +
        `Welcome aboard, <strong>${name}</strong>! 🎉<br>` +
        `Your Registration ID: <strong style="color:var(--tg-accent)">${json.reg_id}</strong><br>` +
        `Please save this ID for event check-in.`,
        [], 300
      );
    } else {
      alert(json.message || "Registration failed. Please try again.");
    }
  } catch {
    alert("Network error. Please check your connection.");
  }
});

// ═════════════════════════════════════════════════════════════════
// FAQ
// ═════════════════════════════════════════════════════════════════

async function askFAQ(query) {
  if (!query.trim()) return;
  const answerDiv = document.getElementById("faqAnswer");
  answerDiv.style.opacity = "0.4";
  answerDiv.textContent   = "Thinking…";
  try {
    const res  = await fetch("/api/faq", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });
    const json = await res.json();
    answerDiv.style.opacity = "1";
    const answer = json.status === "ok" ? json.answer : json.message;
    answerDiv.textContent   = answer;
    speak(answer);    // speak FAQ answer too
  } catch {
    answerDiv.style.opacity = "1";
    answerDiv.textContent   = "Could not reach the bot. Please try again.";
  }
}

document.getElementById("faqAsk").addEventListener("click", () => {
  const q = document.getElementById("faqInput").value.trim();
  if (q) askFAQ(q);
});
document.getElementById("faqInput").addEventListener("keydown", e => {
  if (e.key === "Enter") { const q = document.getElementById("faqInput").value.trim(); if (q) askFAQ(q); }
});
document.querySelectorAll(".faq-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    document.getElementById("faqInput").value = chip.dataset.q;
    askFAQ(chip.dataset.q);
  });
});

// ═════════════════════════════════════════════════════════════════
// Star rating (feedback)
// ═════════════════════════════════════════════════════════════════

const stars      = document.querySelectorAll(".star");
const starLabels = ["", "Poor", "Fair", "Good", "Very Good", "Excellent"];

stars.forEach(star => {
  star.addEventListener("mouseover", () => {
    const v = +star.dataset.v;
    stars.forEach(s => s.classList.toggle("hover", +s.dataset.v <= v));
  });
  star.addEventListener("mouseout", () => { stars.forEach(s => s.classList.remove("hover")); });
  star.addEventListener("click", () => {
    selectedRating = +star.dataset.v;
    stars.forEach(s => s.classList.toggle("active", +s.dataset.v <= selectedRating));
    document.getElementById("starLabel").textContent = starLabels[selectedRating];
  });
});

document.getElementById("submitFeedback").addEventListener("click", async () => {
  if (!selectedRating) { alert("Please select a star rating first."); return; }
  const message = document.getElementById("feedbackMsg").value.trim();
  try {
    const res  = await fetch("/api/feedback", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating: selectedRating, message })
    });
    const json = await res.json();
    if (json.status === "ok") {
      document.getElementById("submitFeedback").style.display  = "none";
      document.getElementById("feedbackMsg").style.display     = "none";
      document.getElementById("starRow").style.pointerEvents   = "none";
      document.getElementById("feedbackSuccess").style.display = "block";
      botReply("💙 <strong>Thank you for your valuable feedback!</strong><br>We will use your feedback to make the next event even better!", [], 300);
    } else {
      alert(json.message || "Submission failed.");
    }
  } catch { alert("Network error. Please try again."); }
});

// ═════════════════════════════════════════════════════════════════
// Main chat — text input + voice input → FAQ API → bot reply
// ═════════════════════════════════════════════════════════════════

const MENU_BUTTONS = [
  { label: "📝 Registration", action: () => handleAction("register")  },
  { label: "📅 Schedule",     action: () => handleAction("schedule")  },
  { label: "📍 Venue",        action: () => handleAction("venue")     },
  { label: "📜 Rules",        action: () => handleAction("rules")     },
  { label: "🏆 Prizes",       action: () => handleAction("prizes")    },
  { label: "⏰ Reminders",    action: () => handleAction("remind")    },
  { label: "❓ FAQ",          action: () => handleAction("faq")       },
  { label: "📞 Helpline",     action: () => handleAction("help")      },
  { label: "⭐ Feedback",     action: () => handleAction("feedback")  },
  { label: "📋 Attendance",   action: () => { window.location.href = "/attendance"; } },
];

function handleAction(action) {
  const labels = {
    register: "📝 Registration", schedule:  "📅 Schedule",
    venue:    "📍 Venue",         rules:     "📜 Rules",
    prizes:   "🏆 Prizes",        remind:    "⏰ Reminders",
    faq:      "❓ FAQ",           help:      "📞 Helpline",
    medical:  "🏥 Medical Helpline", feedback: "⭐ Feedback",
  };
  addMessage(labels[action] || action, "user");

  if (action === "register") {
    document.getElementById("regForm").style.display    = "block";
    document.getElementById("regSuccess").style.display = "none";
  }
  if (action === "medical") {
    buildMedicalGrid();   // load cards before opening
  }
  if (action === "feedback") {
    // reset feedback form each time
    selectedRating = 0;
    document.querySelectorAll(".star").forEach(s => s.classList.remove("active"));
    document.getElementById("starLabel").textContent         = "Tap to rate";
    document.getElementById("feedbackMsg").value             = "";
    document.getElementById("feedbackMsg").style.display     = "block";
    document.getElementById("submitFeedback").style.display  = "block";
    document.getElementById("feedbackSuccess").style.display = "none";
  }
  botReply(getBotIntro(action), [], 500);
  setTimeout(() => openModal(actionToModal(action)), 950);
}

function actionToModal(a) {
  const map = {
    register: "regModal",    schedule:  "schedModal",
    venue:    "venueModal",  rules:     "rulesModal",
    prizes:   "prizesModal", remind:    "remindModal",
    faq:      "faqModal",    help:      "helpModal",
    medical:  "medicalModal", feedback: "feedbackModal",
  };
  return map[a];
}

function getBotIntro(a) {
  const map = {
    register: "Let's get you registered! 📝 Fill in the form and you're all set.",
    schedule: "Here's the full event schedule! 📅",
    venue:    "Here's how to find us! 📍",
    rules:    "Please read the event rules carefully. 📜",
    prizes:   "Check out the certificates & prizes! 🏆",
    remind:   "Your live countdown to the AI Workshop! ⏰",
    faq:      "Ask me anything about the event! ❓",
    help:     "Here is our Helpline information! 📞 Contact us anytime.",
    medical:  "🏥 Here are all Medical & Emergency helpline numbers. Stay safe!",
    feedback: "⭐ We value your opinion! Please rate your experience.",
  };
  return map[a] || "Here you go!";
}

// ── Build Medical Helpline grid from API ──────────────────────────────────────
async function buildMedicalGrid() {
  const grid = document.getElementById("medicalGrid");
  if (!grid || grid.dataset.loaded === "1") return;
  try {
    const res  = await fetch("/api/medical");
    const json = await res.json();
    if (json.status !== "ok") return;
    grid.innerHTML = "";
    const colorMap = {
      red: "#e74c3c", pink: "#e91e8c", orange: "#e67e22",
      blue: "#3498db", purple: "#9b59b6", green: "#27ae60"
    };
    json.data.contacts.forEach(c => {
      const card = document.createElement("div");
      card.className = "medical-card";
      const col = colorMap[c.color] || "var(--tg-accent)";
      card.innerHTML = `
        <div class="mc-color-bar" style="background:${col}"></div>
        <div class="mc-body">
          <div class="mc-name">${c.name}</div>
          <div class="mc-role">${c.role}</div>
          <a class="mc-phone" href="tel:${c.phone}" style="color:${col}">📞 ${c.phone}</a>
          <div class="mc-avail">⏱ ${c.available}</div>
        </div>`;
      grid.appendChild(card);
    });
    grid.dataset.loaded = "1";
  } catch (e) { console.error("Medical grid error:", e); }
}

async function handleUserMessage() {
  const text = userInput.value.trim();
  if (!text) return;
  userInput.value = "";
  addMessage(text, "user");
  showTyping();

  try {
    const res  = await fetch("/api/faq", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: text })
    });
    const json = await res.json();
    hideTyping();
    const reply = json.status === "ok" ? json.answer : ("⚠️ " + json.message);
    addMessage(reply, "bot");
    speak(reply);     // 🔊 bot speaks the reply
  } catch {
    hideTyping();
    addMessage("⚠️ Network error. Please try again.", "bot");
  }
  scrollBottom();
}

sendBtn.addEventListener("click", handleUserMessage);
userInput.addEventListener("keydown", e => { if (e.key === "Enter") handleUserMessage(); });

// ═════════════════════════════════════════════════════════════════
// Welcome message
// ═════════════════════════════════════════════════════════════════

function showWelcome() {
  const welcomeText =
    `<strong>🤖 Event Companion Bot</strong><br><br>` +
    `Hello! 👋 Welcome to <strong>SNJB College of Engineering, Chandwad</strong><br><br>` +
    `I am your smart Event Companion for<br>` +
    `<strong>🧠 AI & Technology Workshop</strong><br>` +
    `<span style="font-size:13px;color:var(--tg-accent)">📅 14 August 2026 &nbsp;|&nbsp; ⏰ 10:00 AM – 4:00 PM &nbsp;|&nbsp; ✅ FREE Entry</span><br><br>` +
    `Organized by: <strong>AIDS Department</strong><br><br>` +
    `I can help you with registration, schedule, venue, rules, certificates, reminders and FAQs.<br><br>` +
    `<span style="font-size:12px;color:var(--tg-muted)">` +
    `🎤 Tap mic to speak  •  🔊 I can speak replies aloud</span>`;

  setTimeout(() => {
    addMessage(welcomeText, "bot", MENU_BUTTONS);
    setTimeout(() => speak(
      "Hello! Welcome to SNJB College of Engineering Chandwad. " +
      "I am your Event Companion for the AI and Technology Workshop on 14 August 2026. " +
      "Registration is completely free. Organized by the AIDS Department. " +
      "How can I help you today?"
    ), 400);
  }, 700);
}

// ═════════════════════════════════════════════════════════════════
// Boot
// ═════════════════════════════════════════════════════════════════

(async function init() {
  initSpeechRecognition();   // Set up mic
  await loadEventData();     // Fetch from Flask
  showWelcome();             // Show greeting + speak it
})();
