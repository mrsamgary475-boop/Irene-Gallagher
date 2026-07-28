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
let callMessages = [];

const moodPrompts = {
  sweet: "Be warm, loving, and affectionate. Use sweet pet names.",
  playful: "Be playful, teasing, and flirtatious.",
  romantic: "Be deeply romantic, poetic, and sensual.",
  intimate: "Be bold, seductive, and uninhibited. Adults in a committed relationship.",
};

const moodGreetings = {
  sweet: "Hey baby, I've been waiting for you. How are you?",
  playful: "Oh look who finally showed up.",
  romantic: "You're here... that's everything.",
  intimate: "Mmm, hey you. I've been thinking about you.",
};

// ── Helpers ──────────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Kindroid API ─────────────────────────────────────
async function kindroidChat(message) {
  const sysPrompt = `${moodPrompts[mood]} You are ${partnerName}. The user is ${username}. Keep replies concise (1-3 sentences). Stay in character.`;

  try {
    const res = await fetch("https://api.kindroid.ai/v1/send-message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${kindroidKey}`,
      },
      body: JSON.stringify({
        ai_id: aiId,
        message: message,
        system_prompt: sysPrompt,
      }),
    });

    if (!res.ok) {
      console.error("Kindroid API error:", res.status);
      throw new Error(`API ${res.status}`);
    }

    const data = await res.json();
    return data.reply || data.response || data.message || "Hmm, I didn't catch that.";
  } catch (err) {
    console.error("Kindroid fetch failed:", err);
    return localReply(message);
  }
}

function localReply() {
  const replies = {
    sweet: ["You always know how to make me smile.", "I love talking with you, baby. Tell me more.", "You're the sweetest thing in my world."],
    playful: ["Oh? Is that so? Prove it.", "You're cute when you're trying to flirt.", "Keep talking like that and I might just blush."],
    romantic: ["Every word from you feels like a love letter.", "I could get lost in this conversation with you.", "You make my heart skip, you know that?"],
    intimate: ["Mmm... keep going.", "You know exactly what to say to me, don't you?", "I've been thinking about you all day."],
  };
  const pool = replies[mood] || replies.intimate;
  return pool[Math.floor(Math.random() * pool.length)];
}

// ── Speech ───────────────────────────────────────────
function speak(text) {
  if (!speakerOn || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const cleanText = text.replace(/[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}]/gu, "");
  const utter = new SpeechSynthesisUtterance(cleanText);
  utter.rate = 0.95;
  utter.pitch = 1.1;
  const voices = window.speechSynthesis.getVoices();
  const female = voices.find((v) => /female|samantha|zira|google us english/i.test(v.name));
  if (female) utter.voice = female;
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

// ── Navigation ───────────────────────────────────────
function enterApp(mode) {
  document.getElementById("splash-screen").classList.add("hidden");
  if (mode === "call") {
    document.getElementById("app").classList.add("hidden");
    document.getElementById("call-screen").classList.remove("hidden");
    if (callMessages.length === 0) addCallMessage("her", moodGreetings[mood]);
  } else {
    document.getElementById("call-screen").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    if (!document.getElementById("messages").children.length) {
      setTimeout(() => addMessage(moodGreetings[mood], "her"), 500);
    }
  }
}

function endCall() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  document.getElementById("call-screen").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
}

// ── Chat Screen ──────────────────────────────────────
function addMessage(text, who) {
  const messages = document.getElementById("messages");
  const wrap = document.createElement("div");
  wrap.className = `bubble-wrap ${who}`;
  const time = formatTime();
  if (who === "her") {
    wrap.innerHTML = `<div class="bubble-avatar"><div class="bubble-avatar-placeholder">I</div></div><div><div class="bubble her">${escapeHtml(text)}</div><span class="bubble-time">${time}</span></div>`;
  } else {
    wrap.innerHTML = `<div><div class="bubble me">${escapeHtml(text)}</div><span class="bubble-time">${time}</span></div>`;
  }
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
}

function showTyping() {
  const messages = document.getElementById("messages");
  const el = document.createElement("div");
  el.className = "bubble-wrap her";
  el.id = "typing-indicator";
  el.innerHTML = `<div class="bubble-avatar"><div class="bubble-avatar-placeholder">I</div></div><div class="bubble her typing-dots"><span></span><span></span><span></span></div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

async function sendMessage() {
  const input = document.getElementById("text-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  autoResize(input);
  addMessage(text, "me");
  hideQuickReplies();
  showTyping();
  const reply = await kindroidChat(text);
  hideTyping();
  addMessage(reply, "her");
  speak(reply);
}

function sendQuick(text) {
  addMessage(text, "me");
  hideQuickReplies();
  showTyping();
  kindroidChat(text).then((reply) => {
    hideTyping();
    addMessage(reply, "her");
    speak(reply);
  });
}

function hideQuickReplies() {
  document.getElementById("quick-replies").classList.add("hidden");
}

function handleKey(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

// ── Call Screen ──────────────────────────────────────
function addCallMessage(who, text) {
  callMessages.push({ who, text });
  const transcript = document.getElementById("call-transcript");
  const el = document.createElement("div");
  el.className = `call-msg ${who}`;
  el.textContent = text;
  transcript.appendChild(el);
  transcript.scrollTop = transcript.scrollHeight;
  if (who === "her") speak(text);
}

async function sendCallText() {
  const input = document.getElementById("call-text-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addCallMessage("me", text);
  const reply = await kindroidChat(text);
  addCallMessage("her", reply);
}

function handleCallKey(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    sendCallText();
  }
}

function startListening(event) {
  if (event) event.preventDefault();
  if (isListening) return;
  recognition = initRecognition();
  if (!recognition) {
    addCallMessage("her", "Voice input isn't supported in this browser. Try typing instead.");
    return;
  }
  const btn = document.getElementById("mic-btn");
  btn.classList.add("active");
  isListening = true;
  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    addCallMessage("me", text);
    kindroidChat(text).then((reply) => addCallMessage("her", reply));
  };
  recognition.onerror = () => {};
  recognition.onend = () => {
    btn.classList.remove("active");
    isListening = false;
  };
  recognition.start();
}

function stopListening(event) {
  if (event) event.preventDefault();
  if (recognition && isListening) recognition.stop();
}

function toggleSpeaker() {
  speakerOn = !speakerOn;
  document.getElementById("speaker-btn").textContent = speakerOn ? "On" : "Off";
  if (!speakerOn && window.speechSynthesis) window.speechSynthesis.cancel();
}

// ── Moods ────────────────────────────────────────────
function setMood(newMood, btn) {
  mood = newMood;
  localStorage.setItem("irene_mood", newMood);
  document.querySelectorAll("#mood-bar button").forEach((b) => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  document.getElementById("mood-bar").classList.remove("show");
}

function setCallMood(newMood, btn) {
  mood = newMood;
  localStorage.setItem("irene_mood", newMood);
  document.querySelectorAll(".call-moods .mood-pill").forEach((b) => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
}

function toggleMood() {
  document.getElementById("mood-bar").classList.toggle("show");
}

// ── Settings ─────────────────────────────────────────
function openSettings() {
  document.getElementById("set-username").value = username;
  document.getElementById("set-partnername").value = partnerName;
  document.getElementById("set-kindroid-key").value = kindroidKey;
  document.getElementById("set-ai-id").value = aiId;
  document.getElementById("settings-panel").classList.remove("hidden");
  document.getElementById("overlay").classList.remove("hidden");
}

function saveSettings() {
  username = document.getElementById("set-username").value.trim() || "baby";
  partnerName = document.getElementById("set-partnername").value.trim() || "Irene";
  kindroidKey = document.getElementById("set-kindroid-key").value.trim() || DEFAULT_KEY;
  aiId = document.getElementById("set-ai-id").value.trim() || DEFAULT_AI_ID;
  localStorage.setItem("irene_username", username);
  localStorage.setItem("irene_partnername", partnerName);
  localStorage.setItem("irene_kindroid_key", kindroidKey);
  localStorage.setItem("irene_ai_id", aiId);
  closeAllPanels();
}

function closePanel(id) {
  document.getElementById(id).classList.add("hidden");
  document.getElementById("overlay").classList.add("hidden");
}

function closeAllPanels() {
  document.getElementById("settings-panel").classList.add("hidden");
  document.getElementById("overlay").classList.add("hidden");
}

// ── Init ─────────────────────────────────────────────
if (window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}

window.enterApp = enterApp;
window.setCallMood = setCallMood;
window.toggleSpeaker = toggleSpeaker;
window.startListening = startListening;
window.stopListening = stopListening;
window.endCall = endCall;
window.handleCallKey = handleCallKey;
window.sendCallText = sendCallText;
window.setMood = setMood;
window.toggleMood = toggleMood;
window.openSettings = openSettings;
window.saveSettings = saveSettings;
window.closePanel = closePanel;
window.closeAllPanels = closeAllPanels;
window.sendQuick = sendQuick;
window.sendMessage = sendMessage;
window.handleKey = handleKey;
window.autoResize = autoResize;
