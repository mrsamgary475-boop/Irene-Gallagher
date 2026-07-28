// ── State ─────────────────────────────────────────────
const DEFAULT_KEY = "kn_9686bcf1-b1dd-424c-b02b-c06e1441449c";
const DEFAULT_AI_ID = "RwTcLQXQ3rMerS7qkZUC";

let mood = localStorage.getItem("irene_mood") || "intimate";
let username = localStorage.getItem("irene_username") || "baby";
let partnerName = localStorage.getItem("irene_partnername") || "Irene";
let kindroidKey = localStorage.getItem("irene_kindroid_key") || DEFAULT_KEY;
let aiId = localStorage.getItem("irene_ai_id") || DEFAULT_AI_ID;
let speakerOn = true;
let recognition = null;
let isListening = false;

const moodGreetings = {
  sweet: "Hey baby, I've been waiting for you. How are you?",
  playful: "Oh look who finally showed up.",
  romantic: "You're here... that's everything.",
  intimate: "Mmm, hey you. I've been thinking about you.",
};

// ── DOM Helpers ──────────────────────────────────────
const $ = (id) => document.getElementById(id);
const avatar = () => $("avatar-orb");
const status = () => $("video-status");

function setAvatarState(state) {
  const a = avatar();
  a.classList.remove("listening", "speaking", "thinking");
  if (state) a.classList.add(state);
}

function setStatus(text, cls) {
  const s = status();
  s.textContent = text;
  s.classList.remove("active", "listening");
  if (cls) s.classList.add(cls);
}

// ── Speech ───────────────────────────────────────────
function speak(text) {
  if (!speakerOn || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const clean = text.replace(/[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}]/gu, "");
  const utter = new SpeechSynthesisUtterance(clean);
  utter.rate = 0.95;
  utter.pitch = 1.1;
  const voices = window.speechSynthesis.getVoices();
  const female = voices.find((v) => /female|samantha|zira|google us english/i.test(v.name));
  if (female) utter.voice = female;
  utter.onstart = () => { setAvatarState("speaking"); setStatus("Speaking...", "active"); };
  utter.onend = () => { setAvatarState(null); setStatus("Tap to talk"); };
  window.speechSynthesis.speak(utter);
}

function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const rec = new SR();
  rec.continuous = false;
  rec.interimResults = false;
  rec.lang = "en-US";
  return rec;
}

// ── Chat API ─────────────────────────────────────────
async function sendToBackend(message) {
  setAvatarState("thinking");
  setStatus("Thinking...", "active");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        mood,
        username,
        partnerName,
        apiKey: kindroidKey,
        aiId,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.reply || "Hmm, I didn't catch that.";
  } catch (err) {
    console.error("Chat failed:", err);
    return "I'm having trouble connecting right now. Try again in a moment.";
  }
}

// ── Transcript ────────────────────────────────────────
function addTranscript(who, text) {
  const t = $("video-transcript");
  const el = document.createElement("div");
  el.className = `transcript-msg ${who}`;
  el.textContent = text;
  t.appendChild(el);
  t.scrollTop = t.scrollHeight;
}

// ── Send / Receive ────────────────────────────────────
async function sendText() {
  const input = $("text-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addTranscript("me", text);
  const reply = await sendToBackend(text);
  addTranscript("her", reply);
  speak(reply);
}

function handleKey(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendText();
  }
}

// ── Voice Input ───────────────────────────────────────
function startListening(event) {
  if (event) event.preventDefault();
  if (isListening) return;
  recognition = initRecognition();
  if (!recognition) {
    addTranscript("her", "Voice input isn't supported in this browser. Try typing instead.");
    return;
  }
  const btn = $("mic-btn");
  btn.classList.add("active");
  isListening = true;
  setAvatarState("listening");
  setStatus("Listening...", "listening");

  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    addTranscript("me", text);
    sendToBackend(text).then((reply) => {
      addTranscript("her", reply);
      speak(reply);
    });
  };
  recognition.onerror = () => {
    setAvatarState(null);
    setStatus("Tap to talk");
  };
  recognition.onend = () => {
    btn.classList.remove("active");
    isListening = false;
    if (!window.speechSynthesis.speaking) {
      setAvatarState(null);
      setStatus("Tap to talk");
    }
  };
  recognition.start();
}

function stopListening(event) {
  if (event) event.preventDefault();
  if (recognition && isListening) recognition.stop();
}

function toggleSpeaker() {
  speakerOn = !speakerOn;
  $("speaker-btn").querySelector(".ctrl-icon").textContent = speakerOn ? "On" : "Off";
  if (!speakerOn && window.speechSynthesis) {
    window.speechSynthesis.cancel();
    setAvatarState(null);
    setStatus("Tap to talk");
  }
}

// ── Moods ────────────────────────────────────────────
function setMood(newMood, btn) {
  mood = newMood;
  localStorage.setItem("irene_mood", newMood);
  document.querySelectorAll(".mood-pill").forEach((b) => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
}

// ── Settings ─────────────────────────────────────────
function openSettings() {
  $("set-username").value = username;
  $("set-partnername").value = partnerName;
  $("set-kindroid-key").value = kindroidKey;
  $("set-ai-id").value = aiId;
  $("settings-panel").classList.remove("hidden");
  $("overlay").classList.remove("hidden");
}

function saveSettings() {
  username = $("set-username").value.trim() || "baby";
  partnerName = $("set-partnername").value.trim() || "Irene";
  kindroidKey = $("set-kindroid-key").value.trim() || DEFAULT_KEY;
  aiId = $("set-ai-id").value.trim() || DEFAULT_AI_ID;
  localStorage.setItem("irene_username", username);
  localStorage.setItem("irene_partnername", partnerName);
  localStorage.setItem("irene_kindroid_key", kindroidKey);
  localStorage.setItem("irene_ai_id", aiId);
  closeAllPanels();
}

function closePanel(id) {
  $(id).classList.add("hidden");
  $("overlay").classList.add("hidden");
}

function closeAllPanels() {
  $("settings-panel").classList.add("hidden");
  $("overlay").classList.add("hidden");
}

// ── Init ─────────────────────────────────────────────
if (window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

setTimeout(() => {
  addTranscript("her", moodGreetings[mood] || moodGreetings.intimate);
}, 800);

// Expose to inline handlers
window.setMood = setMood;
window.toggleSpeaker = toggleSpeaker;
window.startListening = startListening;
window.stopListening = stopListening;
window.openSettings = openSettings;
window.saveSettings = saveSettings;
window.closePanel = closePanel;
window.closeAllPanels = closeAllPanels;
window.sendText = sendText;
window.handleKey = handleKey;
