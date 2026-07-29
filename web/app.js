// ── State ─────────────────────────────────────────────
const DEFAULT_KEY  = "kn_58c5a512-c997-408a-995d-197a04874169";
const DEFAULT_AI   = "RwTcLQXQ3rMerS7qkZUC";
const DEFAULT_IMG  = "https://images.pexels.com/photos/4442079/pexels-photo-4442079.jpeg?auto=compress&cs=tinysrgb&w=1080";

let mood       = localStorage.getItem("irene_mood")       || "intimate";
let username   = localStorage.getItem("irene_username")   || "baby";
let partner    = localStorage.getItem("irene_partnername")|| "Irene";
let apiKey     = localStorage.getItem("irene_kindroid_key")|| DEFAULT_KEY;
let aiId       = localStorage.getItem("irene_ai_id")       || DEFAULT_AI;
let avatarUrl  = localStorage.getItem("irene_avatar_url")  || DEFAULT_IMG;
let speakerOn  = true;
let recognition= null;
let isListening= false;

const greetings = {
  sweet:    "Hey baby, I've been waiting for you. How are you?",
  playful:  "Oh look who finally showed up.",
  romantic: "You're here... that's everything.",
  intimate: "Mmm, hey you. I've been thinking about you.",
};

// ── Helpers ──────────────────────────────────────────
const $ = (id) => document.getElementById(id);

function setAvatarState(state) {
  const bg = $("avatar-bg");
  const badge = $("status-badge");
  bg.classList.remove("listening", "speaking", "thinking");
  badge.classList.remove("listening", "thinking");
  if (state) { bg.classList.add(state); badge.classList.add(state); }
}

function setStatus(text, cls) {
  $("status-text").textContent = text;
  const badge = $("status-badge");
  badge.classList.remove("listening", "thinking");
  if (cls) badge.classList.add(cls);
}

// ── Speech ───────────────────────────────────────────
function speak(text) {
  if (!speakerOn || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const clean = text.replace(/[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}]/gu, "");
  const u = new SpeechSynthesisUtterance(clean);
  u.rate = 0.95; u.pitch = 1.1;
  const voices = window.speechSynthesis.getVoices();
  const f = voices.find(v => /female|samantha|zira|google us english/i.test(v.name));
  if (f) u.voice = f;
  u.onstart = () => { setAvatarState("speaking"); setStatus("Speaking"); };
  u.onend   = () => { setAvatarState(null); setStatus("Connected"); };
  window.speechSynthesis.speak(u);
}

function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const r = new SR();
  r.continuous = false; r.interimResults = false; r.lang = "en-US";
  return r;
}

// ── Chat API ─────────────────────────────────────────
async function sendToBackend(message) {
  setAvatarState("thinking");
  setStatus("Thinking...", "thinking");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, mood, username, partnerName: partner, apiKey, aiId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.reply || "Hmm, I didn't catch that.";
  } catch (err) {
    console.error("Chat error:", err);
    return "I'm having trouble connecting right now.";
  }
}

// ── Transcript ────────────────────────────────────────
function addTranscript(who, text) {
  const t = $("transcript");
  const el = document.createElement("div");
  el.className = `tmsg ${who}`;
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

function handleKey(e) {
  if (e.key === "Enter") { e.preventDefault(); sendText(); }
}

// ── Voice ─────────────────────────────────────────────
function startListening(e) {
  if (e) e.preventDefault();
  if (isListening) return;
  recognition = initRecognition();
  if (!recognition) {
    addTranscript("her", "Voice input isn't supported in this browser. Try typing instead.");
    return;
  }
  $("mic-btn").classList.add("active");
  isListening = true;
  setAvatarState("listening");
  setStatus("Listening...", "listening");

  recognition.onresult = (ev) => {
    const text = ev.results[0][0].transcript;
    addTranscript("me", text);
    sendToBackend(text).then(reply => { addTranscript("her", reply); speak(reply); });
  };
  recognition.onerror = () => { setAvatarState(null); setStatus("Connected"); };
  recognition.onend = () => {
    $("mic-btn").classList.remove("active");
    isListening = false;
    if (!window.speechSynthesis || !window.speechSynthesis.speaking) {
      setAvatarState(null); setStatus("Connected");
    }
  };
  recognition.start();
}

function stopListening(e) {
  if (e) e.preventDefault();
  if (recognition && isListening) recognition.stop();
}

function toggleSpeaker() {
  speakerOn = !speakerOn;
  const btn = $("speaker-btn");
  btn.style.opacity = speakerOn ? "1" : "0.5";
  if (!speakerOn && window.speechSynthesis) {
    window.speechSynthesis.cancel();
    setAvatarState(null); setStatus("Connected");
  }
}

// ── Moods ────────────────────────────────────────────
function setMood(m, btn) {
  mood = m;
  localStorage.setItem("irene_mood", m);
  document.querySelectorAll(".mood-pill").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
}

// ── Fullscreen ───────────────────────────────────────
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
}

// ── End call ─────────────────────────────────────────
function endCall() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  if (recognition && isListening) recognition.stop();
  setStatus("Call Ended");
  setAvatarState(null);
  $("transcript").innerHTML = "";
  setTimeout(() => {
    setStatus("Connected");
    addTranscript("her", greetings[mood] || greetings.intimate);
  }, 1500);
}

// ── Settings ─────────────────────────────────────────
function openSettings() {
  $("set-username").value = username;
  $("set-partnername").value = partner;
  $("set-kindroid-key").value = apiKey;
  $("set-ai-id").value = aiId;
  $("set-avatar-url").value = avatarUrl;
  $("settings-panel").classList.remove("hidden");
  $("overlay").classList.remove("hidden");
}

function saveSettings() {
  username  = $("set-username").value.trim()    || "baby";
  partner   = $("set-partnername").value.trim() || "Irene";
  apiKey    = $("set-kindroid-key").value.trim()|| DEFAULT_KEY;
  aiId      = $("set-ai-id").value.trim()        || DEFAULT_AI;
  avatarUrl = $("set-avatar-url").value.trim()  || DEFAULT_IMG;
  localStorage.setItem("irene_username", username);
  localStorage.setItem("irene_partnername", partner);
  localStorage.setItem("irene_kindroid_key", apiKey);
  localStorage.setItem("irene_ai_id", aiId);
  localStorage.setItem("irene_avatar_url", avatarUrl);
  $("avatar-img").src = avatarUrl;
  closeAllPanels();
}

function closePanel(id) { $(id).classList.add("hidden"); $("overlay").classList.add("hidden"); }
function closeAllPanels() { $("settings-panel").classList.add("hidden"); $("overlay").classList.add("hidden"); }

// ── Init ─────────────────────────────────────────────
if (window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
$("avatar-img").src = avatarUrl;
setTimeout(() => addTranscript("her", greetings[mood] || greetings.intimate), 800);

window.setMood = setMood;
window.toggleSpeaker = toggleSpeaker;
window.toggleFullscreen = toggleFullscreen;
window.startListening = startListening;
window.stopListening = stopListening;
window.endCall = endCall;
window.openSettings = openSettings;
window.saveSettings = saveSettings;
window.closePanel = closePanel;
window.closeAllPanels = closeAllPanels;
window.sendText = sendText;
window.handleKey = handleKey;
