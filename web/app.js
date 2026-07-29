// ── Constants ────────────────────────────────────────
const DEFAULT_KEY = "kn_58c5a512-c997-408a-995d-197a04874169";
const DEFAULT_AI  = "RwTcLQXQ3rMerS7qkZUC";

// ── State ─────────────────────────────────────────────
let mood       = localStorage.getItem("irene_mood")        || "intimate";
let username   = localStorage.getItem("irene_username")    || "baby";
let partner    = localStorage.getItem("irene_partnername") || "Irene";
let apiKey     = localStorage.getItem("irene_kindroid_key")|| DEFAULT_KEY;
let aiId       = localStorage.getItem("irene_ai_id")       || DEFAULT_AI;
let callActive = false;
let recognition = null;
let isListening = false;

const greetings = {
  sweet:    "Hey baby, I've been waiting for you. How are you?",
  playful:  "Oh look who finally showed up.",
  romantic: "You're here... that's everything.",
  intimate: "Mmm, hey you. I've been thinking about you.",
};

// ── DOM ───────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

// ── Top badge state ───────────────────────────────────
function setBadge(sub, dotCls) {
  $("top-sub").textContent = sub;
  const dot = $("top-dot");
  dot.classList.remove("listening", "thinking");
  if (dotCls) dot.classList.add(dotCls);
}

// ── Speech synthesis ──────────────────────────────────
function shouldSpeak() {
  return $("speak-toggle").checked && !!window.speechSynthesis;
}

function speak(text) {
  if (!shouldSpeak()) return;
  window.speechSynthesis.cancel();
  const clean = text.replace(/[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}]/gu, "");
  const u = new SpeechSynthesisUtterance(clean);
  u.rate = 0.95; u.pitch = 1.1;
  const voices = window.speechSynthesis.getVoices();
  const f = voices.find(v => /female|samantha|zira|google us english/i.test(v.name));
  if (f) u.voice = f;
  u.onstart = () => setBadge("Speaking...");
  u.onend   = () => setBadge(callActive ? "In call" : "Kindroid connected");
  window.speechSynthesis.speak(u);
}

// ── Chat API ─────────────────────────────────────────
const MOOD_PROMPTS = {
  sweet:    "Be warm, loving, and affectionate. Use sweet pet names.",
  playful:  "Be playful, teasing, and flirtatious.",
  romantic: "Be deeply romantic, poetic, and sensual.",
  intimate: "Be bold, seductive, and uninhibited. Adults in a committed relationship.",
};

async function sendToBackend(message) {
  setBadge("Thinking...", "thinking");
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
  } finally {
    setBadge(callActive ? "In call" : "Kindroid connected");
  }
}

// ── Transcript ────────────────────────────────────────
function addMsg(who, text) {
  const t = $("transcript");
  const el = document.createElement("div");
  el.className = `tmsg ${who}`;
  el.textContent = text;
  t.appendChild(el);
  t.scrollTop = t.scrollHeight;
}

// ── Send ─────────────────────────────────────────────
async function sendText() {
  const input = $("text-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMsg("me", text);
  const reply = await sendToBackend(text);
  addMsg("her", reply);
  speak(reply);
  if ($("textme-toggle").checked) {
    console.log("[Text me]", reply);
  }
}

function handleKey(e) {
  if (e.key === "Enter") { e.preventDefault(); sendText(); }
}

// ── Voice ─────────────────────────────────────────────
function initRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const r = new SR();
  r.continuous = false; r.interimResults = false; r.lang = "en-US";
  return r;
}

function startListening(e) {
  if (e) e.preventDefault();
  if (isListening) return;
  recognition = initRecognition();
  if (!recognition) {
    addMsg("her", "Voice input isn't supported in this browser. Try typing instead.");
    return;
  }
  $("hold-btn").classList.add("active");
  $("mic-status-btn").textContent = "Mic active";
  $("mic-status-btn").classList.add("active");
  isListening = true;
  setBadge("Listening...", "listening");

  recognition.onresult = (ev) => {
    const text = ev.results[0][0].transcript;
    addMsg("me", text);
    sendToBackend(text).then(reply => { addMsg("her", reply); speak(reply); });
  };
  recognition.onerror = () => resetMicUI();
  recognition.onend   = () => resetMicUI();
  recognition.start();
}

function stopListening(e) {
  if (e) e.preventDefault();
  if (recognition && isListening) recognition.stop();
}

function resetMicUI() {
  $("hold-btn").classList.remove("active");
  $("mic-status-btn").textContent = "Mic ready";
  $("mic-status-btn").classList.remove("active");
  isListening = false;
  setBadge(callActive ? "In call" : "Kindroid connected");
}

// ── Call toggle ───────────────────────────────────────
function toggleCall() {
  callActive = !callActive;
  const btn = $("call-btn");
  if (callActive) {
    btn.textContent = "End call";
    btn.classList.add("active");
    setBadge("In call");
    addMsg("her", greetings[mood] || greetings.intimate);
  } else {
    btn.textContent = "Start call";
    btn.classList.remove("active");
    setBadge("Kindroid connected");
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (recognition && isListening) recognition.stop();
    $("transcript").innerHTML = "";
  }
}

// ── Camera toggle ─────────────────────────────────────
function toggleCamera() {
  const btn = $("camera-btn");
  const video = $("bg-video");
  const isMuted = video.hasAttribute("data-cam-off");
  if (isMuted) {
    video.removeAttribute("data-cam-off");
    video.style.opacity = "1";
    btn.textContent = "Camera off";
  } else {
    video.setAttribute("data-cam-off", "1");
    video.style.opacity = "0.15";
    btn.textContent = "Camera on";
    btn.classList.add("active");
    // revert active style after toggle
    setTimeout(() => btn.classList.remove("active"), 150);
  }
}

// ── Fullscreen ────────────────────────────────────────
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen().catch(() => {});
  }
}

document.addEventListener("fullscreenchange", () => {
  $("fullscreen-btn").textContent =
    document.fullscreenElement ? "Exit full screen" : "Full screen";
});

// ── Settings ─────────────────────────────────────────
function openSettings() {
  $("set-username").value    = username;
  $("set-partnername").value = partner;
  $("set-kindroid-key").value= apiKey;
  $("set-ai-id").value       = aiId;
  $("set-mood").value        = mood;
  $("settings-panel").classList.remove("hidden");
  $("overlay").classList.remove("hidden");
}

function saveSettings() {
  username  = $("set-username").value.trim()     || "baby";
  partner   = $("set-partnername").value.trim()  || "Irene";
  apiKey    = $("set-kindroid-key").value.trim() || DEFAULT_KEY;
  aiId      = $("set-ai-id").value.trim()        || DEFAULT_AI;
  mood      = $("set-mood").value;
  localStorage.setItem("irene_username",    username);
  localStorage.setItem("irene_partnername", partner);
  localStorage.setItem("irene_kindroid_key",apiKey);
  localStorage.setItem("irene_ai_id",       aiId);
  localStorage.setItem("irene_mood",        mood);
  closePanel();
}

function closePanel() {
  $("settings-panel").classList.add("hidden");
  $("overlay").classList.add("hidden");
}

// ── Long-press badge to open settings ────────────────
let pressTimer = null;
$("top-badge").addEventListener("mousedown",  () => { pressTimer = setTimeout(openSettings, 600); });
$("top-badge").addEventListener("touchstart", () => { pressTimer = setTimeout(openSettings, 600); }, {passive:true});
["mouseup","mouseleave","touchend","touchcancel"].forEach(ev =>
  $("top-badge").addEventListener(ev, () => clearTimeout(pressTimer))
);

// ── Init ─────────────────────────────────────────────
if (window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}

// Make functions available to inline handlers
window.toggleCall       = toggleCall;
window.toggleCamera     = toggleCamera;
window.toggleFullscreen = toggleFullscreen;
window.startListening   = startListening;
window.stopListening    = stopListening;
window.sendText         = sendText;
window.handleKey        = handleKey;
window.saveSettings     = saveSettings;
window.closePanel       = closePanel;
