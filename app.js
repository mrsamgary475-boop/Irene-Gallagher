/* =============================================
   IRENE PWA — App Logic
   Kindroid AI + Video Call + Chat
   ============================================= */

// ── Pre-configured credentials ─────────────────
// (baked in so no manual setup needed)
const KINDROID_KEY_DEFAULT  = 'kn_9686bcf1-b1dd-424c-b02b-c06e1441449c';
const KINDROID_AI_ID_DEFAULT = 'RwTcLQXQ3rMerS7qkZUC';

// ── State ──────────────────────────────────────
let currentMood  = localStorage.getItem('irene_mood')        || 'intimate';
let userName     = localStorage.getItem('irene_username')    || 'baby';
let partnerName  = localStorage.getItem('irene_partnername') || 'Irene';
let kindroidKey  = localStorage.getItem('irene_kindroid_key')|| KINDROID_KEY_DEFAULT;
let kindroidAiId = localStorage.getItem('irene_ai_id')       || KINDROID_AI_ID_DEFAULT;
let speakerOn    = true;
let recognition  = null;
let callActive   = false;

// ── Mood context for Kindroid ──────────────────
const moodContext = {
  sweet:    'Be warm, loving, and affectionate. Use sweet pet names.',
  playful:  'Be playful, teasing, and flirtatious.',
  romantic: 'Be deeply romantic, poetic, and sensual.',
  intimate: 'Be bold, seductive, and uninhibited. Adults in a committed relationship.'
};

const openingMessages = {
  sweet:    `Hey baby 💕 I've been waiting for you. How are you?`,
  playful:  `Oh look who finally showed up 😏`,
  romantic: `You're here… that's everything 🌹`,
  intimate: `Mmm, hey you 🔥 I've been thinking about you…`
};

// ── Enter App ──────────────────────────────────
function enterApp(mode) {
  document.getElementById('splash-screen').classList.add('hidden');
  if (mode === 'call') {
    startCall();
  } else {
    document.getElementById('app').classList.remove('hidden');
    setTimeout(() => addMessage(openingMessages[currentMood], 'her'), 600);
  }
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  }
}

// ══════════════════════════════════════════════
//  VIDEO CALL
// ══════════════════════════════════════════════
function startCall() {
  callActive = true;
  document.getElementById('app').classList.add('hidden');
  document.getElementById('call-screen').classList.remove('hidden');
  setCallStatus('Connected ❤️');

  setTimeout(() => {
    const greeting = {
      sweet:    `Hey ${userName}... 💕 so good to see you`,
      playful:  `Oh you finally called 😏 I was starting to wonder`,
      romantic: `There you are… I've been waiting 🌹`,
      intimate: `Mmm, hey you 🔥 I love seeing your face`
    };
    showCallBubble(greeting[currentMood] || greeting.sweet, true);
  }, 800);
}

function endCall() {
  callActive = false;
  stopSpeech();
  if (recognition) { try { recognition.stop(); } catch(e) {} }
  document.getElementById('call-screen').classList.add('hidden');
  document.getElementById('splash-screen').classList.remove('hidden');
}

function switchToChat() {
  callActive = false;
  stopSpeech();
  if (recognition) { try { recognition.stop(); } catch(e) {} }
  document.getElementById('call-screen').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  if (document.getElementById('messages').children.length === 0) {
    setTimeout(() => addMessage(openingMessages[currentMood], 'her'), 400);
  }
}

function setCallStatus(text) {
  document.getElementById('call-status-text').textContent = text;
}

function setCallMood(mood) {
  currentMood = mood;
  localStorage.setItem('irene_mood', mood);
  document.querySelectorAll('.mood-pill').forEach(btn => btn.classList.remove('active'));
  event.currentTarget.classList.add('active');
}

function showCallBubble(text, speak) {
  const bubble     = document.getElementById('call-bubble');
  const bubbleText = document.getElementById('call-bubble-text');
  bubbleText.textContent = text;
  bubble.classList.remove('hidden');
  bubble.classList.add('visible');
  if (speak && speakerOn) speakText(text);
  setTimeout(() => {
    bubble.classList.remove('visible');
    setTimeout(() => bubble.classList.add('hidden'), 600);
  }, Math.max(4000, text.length * 60));
}

// ── Web Speech — hold to talk ──────────────────
function startListening(e) {
  e.preventDefault();
  const btn = document.getElementById('mic-btn');
  btn.classList.add('listening');
  document.getElementById('mic-wave').classList.remove('hidden');
  setCallStatus('Listening… 🎙️');

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    document.getElementById('call-type-row').style.opacity = '1';
    document.getElementById('call-text-input').focus();
    btn.classList.remove('listening');
    document.getElementById('mic-wave').classList.add('hidden');
    setCallStatus('Type below 👇');
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous    = false;
  recognition.interimResults = false;
  recognition.lang           = 'en-US';

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    sendCallMessage(transcript);
  };
  recognition.onerror = () => {
    setCallStatus('Mic error — type below');
    document.getElementById('call-type-row').style.opacity = '1';
  };
  recognition.onend = () => {
    btn.classList.remove('listening');
    document.getElementById('mic-wave').classList.add('hidden');
  };
  recognition.start();
}

function stopListening(e) {
  e.preventDefault();
  document.getElementById('mic-btn').classList.remove('listening');
  document.getElementById('mic-wave').classList.add('hidden');
  if (recognition) { try { recognition.stop(); } catch(e) {} }
}

async function sendCallMessage(text) {
  if (!text.trim()) return;
  setCallStatus(`You: "${text.substring(0,30)}${text.length>30?'…':''}"`);
  const reply = await fetchKindroid(text);
  if (reply) {
    showCallBubble(reply, true);
    setCallStatus('Connected ❤️');
  }
}

function handleCallKey(e) {
  if (e.key === 'Enter') sendCallText();
}

function sendCallText() {
  const input = document.getElementById('call-text-input');
  const text  = input.value.trim();
  if (!text) return;
  input.value = '';
  sendCallMessage(text);
}

// ── Speaker / TTS ──────────────────────────────
function toggleSpeaker() {
  speakerOn = !speakerOn;
  document.getElementById('speaker-btn').style.opacity = speakerOn ? '1' : '0.4';
  if (!speakerOn) stopSpeech();
}

function speakText(text) {
  if (!speakerOn || !window.speechSynthesis) return;
  stopSpeech();
  const clean = text.replace(/[💕🔥🌹😏🌸❤️😈✦]/g, '').trim();
  const utt   = new SpeechSynthesisUtterance(clean);
  utt.rate  = 0.92;
  utt.pitch = 1.15;
  utt.volume = 1;
  const voices       = window.speechSynthesis.getVoices();
  const femaleVoice  = voices.find(v =>
    v.name.toLowerCase().includes('aria') ||
    v.name.toLowerCase().includes('zira') ||
    (v.lang === 'en-US' && v.name.toLowerCase().includes('google'))
  ) || voices.find(v => v.lang.startsWith('en'));
  if (femaleVoice) utt.voice = femaleVoice;
  window.speechSynthesis.speak(utt);
}

function stopSpeech() {
  if (window.speechSynthesis) window.speechSynthesis.cancel();
}

// ══════════════════════════════════════════════
//  KINDROID API
// ══════════════════════════════════════════════
async function fetchKindroid(userText) {
  try {
    // Try multiple endpoints for compatibility
    const endpoints = [
      {
        url: 'https://api.kindroid.ai/v1/send-message',
        body: {
          ai_id: kindroidAiId,
          message: userText,
          stream: false
        }
      },
      {
        url: 'https://api.kindroid.ai/v1/characters/' + kindroidAiId + '/chat',
        body: {
          character_code: kindroidAiId,
          message: userText
        }
      },
      {
        url: 'https://api.kindroid.ai/v1/send-ai-message',
        body: {
          ai_id: kindroidAiId,
          message: userText,
          system_note: moodContext[currentMood] || moodContext.intimate
        }
      }
    ];

    for (const endpoint of endpoints) {
      try {
        const res = await fetch(endpoint.url, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${kindroidKey}`,
            'Content-Type':  'application/json'
          },
          body: JSON.stringify(endpoint.body)
        });
        if (res.ok) {
          const data = await res.json();
          return data.message || data.response || data.text || data.content || null;
        }
      } catch (e) {
        console.log('Endpoint failed:', endpoint.url, e);
        continue;
      }
    }
    
    return "Something went wrong, try again baby 💕";
  } catch (e) {
    console.error('Kindroid error:', e);
    return "Connection dropped for a second… come back? 💕";
  }
}

// ══════════════════════════════════════════════
//  CHAT
// ══════════════════════════════════════════════
async function getIreneResponse(userText) {
  showTyping();
  const reply = await fetchKindroid(userText);
  hideTyping();
  if (reply) addMessage(reply, 'her');
}

function sendMessage() {
  const input = document.getElementById('user-input');
  const text  = input.value.trim();
  if (!text) return;
  input.value = ''; input.style.height = 'auto';
  addMessage(text, 'me');
  hideQuickReplies();
  getIreneResponse(text);
}

function sendQuick(text) {
  addMessage(text, 'me');
  hideQuickReplies();
  getIreneResponse(text);
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function addMessage(text, sender) {
  const messages = document.getElementById('messages');
  const wrap     = document.createElement('div');
  wrap.className = `bubble-wrap ${sender}`;
  const time     = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  wrap.innerHTML = sender === 'her'
    ? `<div class="bubble-avatar"><video src="irene_avatar.mp4" autoplay loop muted playsinline></video></div>
       <div><div class="bubble her">${escapeHtml(text)}</div><span class="bubble-time">${time}</span></div>`
    : `<div><div class="bubble me">${escapeHtml(text)}</div><span class="bubble-time">${time}</span></div>`;
  messages.appendChild(wrap);
  scrollToBottom();
}

function showTyping() {
  const messages = document.getElementById('messages');
  const el = document.createElement('div');
  el.className = 'bubble-wrap her'; el.id = 'typing-indicator';
  el.innerHTML = `<div class="bubble-avatar"><video src="irene_avatar.mp4" autoplay loop muted playsinline></video></div>
    <div class="bubble her typing-dots"><span></span><span></span><span></span></div>`;
  messages.appendChild(el);
  scrollToBottom();
}

function hideTyping() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

function scrollToBottom() {
  document.getElementById('chat-area').scrollTop = document.getElementById('chat-area').scrollHeight;
}

function escapeHtml(t) {
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');
}

function hideQuickReplies() {
  document.getElementById('quick-replies').style.opacity = '0.4';
}

// ── Mood ────────────────────────────────────────
function toggleMood() { document.getElementById('mood-bar').classList.toggle('hidden'); }
function setMood(mood) {
  currentMood = mood;
  localStorage.setItem('irene_mood', mood);
  document.getElementById('mood-bar').classList.add('hidden');
  document.getElementById('quick-replies').style.opacity = '1';
  const acks = {
    sweet:'Aww sweet mode 💕', playful:'Playful mode 😏 you asked for it!',
    romantic:'Romantic… my favorite 🌹', intimate:'Oh it\'s THAT kind of night 🔥'
  };
  addMessage(acks[mood], 'her');
}

// ── Settings ────────────────────────────────────
function openSettings() {
  document.getElementById('s-partner-name').value = partnerName;
  document.getElementById('s-user-name').value    = userName;
  document.getElementById('s-mood').value         = currentMood;
  document.getElementById('s-ai-id').value        = kindroidAiId;
  document.getElementById('s-api-key').value      = kindroidKey ? '••••••••' : '';
  openPanel('settings-panel');
}

function saveSettings() {
  partnerName  = document.getElementById('s-partner-name').value.trim() || 'Irene';
  userName     = document.getElementById('s-user-name').value.trim()    || 'baby';
  currentMood  = document.getElementById('s-mood').value;
  const newId  = document.getElementById('s-ai-id').value.trim();
  const newKey = document.getElementById('s-api-key').value;
  if (newId)  kindroidAiId = newId;
  if (newKey && !newKey.startsWith('•')) kindroidKey = newKey;
  localStorage.setItem('irene_partnername', partnerName);
  localStorage.setItem('irene_username',    userName);
  localStorage.setItem('irene_mood',        currentMood);
  localStorage.setItem('irene_ai_id',       kindroidAiId);
  if (kindroidKey) localStorage.setItem('irene_kindroid_key', kindroidKey);
  closePanel('settings-panel');
  addMessage(`Got it baby 💕 I'm ${partnerName}, you're ${userName}.`, 'her');
  document.getElementById('display-name').textContent = partnerName;
}

// ── Panels ──────────────────────────────────────
function openPanel(id) {
  document.getElementById(id).classList.remove('hidden');
  document.getElementById('overlay').classList.remove('hidden');
}
function closePanel(id) {
  document.getElementById(id).classList.add('hidden');
  document.getElementById('overlay').classList.add('hidden');
}
function closeAllPanels() {
  ['settings-panel'].forEach(id => document.getElementById(id).classList.add('hidden'));
  document.getElementById('overlay').classList.add('hidden');
}

// Load voices async (browser requirement)
if (window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
}
