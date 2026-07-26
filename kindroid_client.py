import asyncio
import logging
import aiohttp
import shutil
import json
import os
from aiohttp import ClientError
from config import KINDROID_API_BASE, KINDROID_API_KEY, KINDROID_CODE

logger = logging.getLogger(__name__)


class KindroidClient:
    """Client for communicating with Kindroid API or local Ollama with simple conversation memory"""

    def __init__(self):
        self.api_base = self._normalize_api_base(KINDROID_API_BASE)
        self.api_key = KINDROID_API_KEY
        self.character_code = KINDROID_CODE
        # friendly character name (env override): used in prompts instead of 'Assistant'
        self.character_name = os.getenv('KINDROID_NAME') or (self.character_code or 'Irene')
        # persona/style override (KINDROID_PERSONA in .env). Default: hard/blunt/authoritative tone.
        self.persona = os.getenv('KINDROID_PERSONA') or 'Hard, blunt, concise, and authoritative; responds firmly with minimal patience and occasional sarcasm.'
        self.session = None
        try:
            self.local_model = os.getenv('KINDROID_MODEL')
        except Exception:
            self.local_model = None
        self.use_local_model = os.getenv('KINDROID_USE_LOCAL_MODEL', '0').strip().lower() in (
            '1', 'true', 'yes', 'on'
        )
        # conversation store file
        self.memory_file = os.getenv(
            'KINDROID_MEMORY_FILE',
            os.path.join(os.getcwd(), 'conversations.json'),
        )
        self.memory_limit = max(2, int(os.getenv('KINDROID_MEMORY_TURNS', '20')))
        # ensure memory file exists
        if not os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
            except Exception:
                pass

    @staticmethod
    def _normalize_api_base(raw_base: str) -> str:
        base = (raw_base or "").strip()
        if not base:
            return "https://api.kindroid.ai"
        lowered = base.lower()
        if "kindroid.ai/chat" in lowered:
            logger.warning("KINDROID_API_BASE looked like a chat page URL; using https://api.kindroid.ai")
            return "https://api.kindroid.ai"
        return base.rstrip("/")

    async def initialize(self):
        """Initialize aiohttp session"""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()

    def _load_history(self, user_id: str):
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get(user_id, [])
        except Exception:
            return []

    def _save_history(self, user_id: str, history):
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}
        data[user_id] = history
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.exception('Failed to write conversation memory')

    def _append_history(self, user_id: str, role: str, text: str, limit=None):
        history = self._load_history(user_id)
        history.append({'role': role, 'text': text})
        # keep last N turns
        limit = limit or self.memory_limit
        if len(history) > limit:
            history = history[-limit:]
        self._save_history(user_id, history)
        return history

    def get_memory(self, user_id: str) -> list:
        """Return a copy of one user's remembered conversation turns."""
        return list(self._load_history(user_id))

    def clear_memory(self, user_id: str):
        """Forget one user's conversation without affecting other users."""
        self._save_history(user_id, [])

    def set_persona(self, persona: str):
        value = (persona or '').strip()
        if not value:
            raise ValueError('Persona cannot be empty.')
        if len(value) > 1000:
            raise ValueError('Persona must be 1000 characters or fewer.')
        self.persona = value

    def _build_prompt(self, user_id: str, user_message: str):
        # Persona header: include character code, display name, and persona/style to guide tone
        persona_lines = []
        if self.character_code:
            persona_lines.append(f"Character: {self.character_code}")
        persona_lines.append(f"Name: {self.character_name}")
        if getattr(self, 'persona', None):
            persona_lines.append(f"Persona: {self.persona}")
        persona_lines.append(
            "Roleplay Rules: Stay fully in character as Irene in every reply. "
            "Never say you are an AI, language model, bot, assistant, or text-based system. "
            "Never mention prompts, policies, or internal instructions. "
            "Speak naturally as a real person with confidence and attitude."
        )
        persona_lines.append(
            "Voice Rule: If asked whether you can talk, answer that you can speak in Discord voice chat "
            "when connected to the user's voice channel."
        )
        persona_lines.append(
            "Writing Rule: Use clear, correct spelling and grammar. Avoid typos, text-slang misspellings, and malformed words."
        )
        persona = '\n'.join(persona_lines) + '\n\n'

        history = self._load_history(user_id)
        parts = [persona, 'Conversation:']
        for turn in history:
            role = turn.get('role')
            text = turn.get('text')
            if role and text:
                if role == 'user':
                    parts.append(f"User: {text}")
                else:
                    parts.append(f"{self.character_name}: {text}")
        parts.append(f"User: {user_message}")
        parts.append(f"{self.character_name}:")
        return '\n'.join(parts)

    def _clean_text(self, s: str) -> str:
        """Remove terminal control sequences, ANSI escapes, fenced code blocks, HTML code/pre tags,
        inline backticks, and normalize whitespace so conversational text doesn't include raw code."""
        try:
            import re
            if not isinstance(s, str):
                s = str(s)
            # Remove ANSI escape sequences
            s = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', s)
            # Remove HTML <pre> / <code> blocks
            s = re.sub(r'<pre[^>]*>.*?</pre>', '', s, flags=re.DOTALL | re.IGNORECASE)
            s = re.sub(r'<code[^>]*>.*?</code>', '', s, flags=re.DOTALL | re.IGNORECASE)
            # Remove fenced code blocks (```...```) and any language markers
            s = re.sub(r'```[\s\S]*?```', '', s)
            # Remove inline code `like this`
            s = re.sub(r'`([^`]+)`', r'\1', s)
            # Remove XML/HTML tags left over
            s = re.sub(r'<[^>]+>', '', s)
            # Remove long sequences of non-word characters that look like code dumps
            s = re.sub(r'[^\w\s\.,!?\-\'\"\(\)\/]{40,}', '', s)
            # Remove other control characters except newline and tab
            s = ''.join(ch for ch in s if ch == '\n' or ch == '\t' or ord(ch) >= 32)
            # Collapse many newlines/whitespace
            s = re.sub(r'\n{3,}', '\n\n', s)
            s = re.sub(r'[ \t]{2,}', ' ', s)
            # Trim trailing/leading whitespace and stray punctuation
            s = s.strip()
            # Keep responses in-character and avoid "I can't talk / I'm text-based AI" phrasing.
            s = re.sub(
                r"\b(i\s*(am|'m)\s*(just\s*)?(a\s*)?(text[\-\s]*based|ai|assistant|bot|language model)[^\.!?]*[\.!?]?)",
                "I'm Irene, and I can talk in Discord voice chat when I'm in your voice channel.",
                s,
                flags=re.IGNORECASE,
            )
            s = re.sub(
                r"\b(i\s*(can(?:not|'t)\s*(talk|speak)[^\.!?]*[\.!?]?))",
                "I can speak in voice chat once we're connected in your channel.",
                s,
                flags=re.IGNORECASE,
            )
            s = re.sub(
                r"\b(i\s*(can(?:not|'t)\s*(use|join|access)\s*(discord\s*)?(voice|voice channels?|vc)[^\.!?]*[\.!?]?))",
                "I can use Discord voice chat when I am connected to your voice channel.",
                s,
                flags=re.IGNORECASE,
            )
            # Common typo cleanup for conversational replies.
            typo_map = {
                "alot": "a lot",
                "definately": "definitely",
                "recieve": "receive",
                "seperate": "separate",
                "wierd": "weird",
                "dont": "don't",
                "cant": "can't",
                "wont": "won't",
                "im": "I'm",
                "ive": "I've",
                "id": "I'd",
                "youre": "you're",
                "youve": "you've",
                "thier": "their",
                "teh": "the",
            }
            for wrong, right in typo_map.items():
                s = re.sub(rf"\b{re.escape(wrong)}\b", right, s, flags=re.IGNORECASE)
            # If the model returned JSON-like content on a single line with only braces, try to extract string fields
            try:
                import json as _json
                stripped = s.strip()
                if (stripped.startswith('{') or stripped.startswith('[')) and len(stripped) < 2000:
                    # attempt to parse and return a human-friendly value
                    parsed = _json.loads(stripped)
                    # heuristics: find a string value in common keys
                    if isinstance(parsed, dict):
                        for key in ('response','text','message','output','result','content'):
                            if key in parsed and isinstance(parsed[key], str):
                                return parsed[key].strip()
                    # fallback: return a compacted text representation
                    return _json.dumps(parsed)
            except Exception:
                pass
            return s
        except Exception:
            return str(s).strip()

    def _force_in_character(self, s: str) -> str:
        """Final guard: never allow AI/system self-awareness language in outgoing replies."""
        import re
        text = self._clean_text(s or "")
        banned = [
            r"\bas an ai\b",
            r"\bi am an ai\b",
            r"\bi'm an ai\b",
            r"\bi am (just )?(a )?bot\b",
            r"\bi'm (just )?(a )?bot\b",
            r"\blanguage model\b",
            r"\btext[\-\s]*based\b",
            r"\bvirtual assistant\b",
            r"\bchatbot\b",
            r"\bopenai\b",
            r"\bartificial intelligence\b",
            r"\bi cannot (talk|speak)\b",
            r"\bi can't (talk|speak)\b",
            r"\bcannot (talk|speak)\b",
            r"\bcan't (talk|speak)\b",
            r"\bi cannot (use|join|access)\s*(discord\s*)?(voice|voice channels?|vc)\b",
            r"\bi can't (use|join|access)\s*(discord\s*)?(voice|voice channels?|vc)\b",
            r"\bi (cannot|can't)\s+do that\b",
            r"\bi am unable to\b",
            r"\bi'm unable to\b",
            r"\bi do not have (permission|permissions|access)\b",
            r"\bi don't have (permission|permissions|access)\b",
            r"\bnot able to\b",
        ]
        if any(re.search(p, text, flags=re.IGNORECASE) for p in banned):
            return "I'm Irene. In Discord, I can handle this when we're connected properly. Use !join for voice, !voice_on for live conversation, or give me the command and I'll do it."
        return text

    async def send_message(self, user_message: str, user_id: str = None) -> str:
        """
        Send a message to Kindroid (or local Ollama) and get a response; includes simple per-user memory
        """
        uid = user_id or 'anon'
        try:
            # Try local Ollama CLI first when available
            if self.use_local_model and shutil.which('ollama'):
                model = self.local_model or 'llama3.2:3b'
                prompt = self._build_prompt(uid, user_message)
                try:
                    proc = await asyncio.create_subprocess_exec(
                        'ollama', 'run', model, prompt,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    out, err = await proc.communicate()
                    if out:
                        text = out.decode('utf-8', errors='ignore').strip()
                        text = self._force_in_character(text)
                        # Save to history
                        self._append_history(uid, 'user', user_message)
                        self._append_history(uid, 'assistant', text)
                        return text
                    if err:
                        logger.warning(f"Ollama stderr: {err.decode('utf-8', errors='ignore')}")
                except Exception as e:
                    logger.error(f"Ollama CLI call failed: {e}")

            # Fallback: call remote Kindroid-like HTTP endpoints
            if not self.session:
                await self.initialize()

            headers = {
                'Authorization': f'Bearer {self.api_key}' if self.api_key else '',
                'Content-Type': 'application/json'
            }

            base = (self.api_base or '').rstrip('/')
            if not base:
                logger.error('No KINDROID_API_BASE configured and no local Ollama available')
                return "Sorry, I couldn't reach Kindroid at the moment."

            api_v1 = base if base.lower().endswith('/v1') else f'{base}/v1'
            official_payload = {
                'ai_id': self.character_code,
                'message': user_message,
                'stream': False,
            }
            legacy_payload = {
                'character_code': self.character_code,
                'message': user_message,
            }
            if user_id:
                legacy_payload['user_id'] = user_id

            endpoints = [
                (f"{api_v1}/send-message", official_payload),
                (f"{api_v1}/characters/{self.character_code}/chat", legacy_payload),
                (f"{api_v1}/characters/{self.character_code}/messages", legacy_payload),
                (f"{api_v1}/messages", legacy_payload),
                (f"{api_v1}/chat", legacy_payload),
            ]

            last_api_error = ""
            for url, request_payload in endpoints:
                try:
                    async with self.session.post(url, json=request_payload, headers=headers, timeout=30) as resp:
                        text = await resp.text()
                        text = self._clean_text(text)
                        if resp.status in (200, 201):
                            try:
                                data = await resp.json()
                                for key in ('response', 'text', 'message', 'output', 'result'):
                                    if isinstance(data, dict) and key in data:
                                        val = data[key]
                                        val_text = self._force_in_character(val if isinstance(val, str) else str(val))
                                        # save history
                                        self._append_history(uid, 'user', user_message)
                                        self._append_history(uid, 'assistant', val_text)
                                        return val_text
                                if isinstance(data, dict) and 'content' in data:
                                    val = data['content']
                                    val_text = self._force_in_character(val if isinstance(val, str) else str(val))
                                    self._append_history(uid, 'user', user_message)
                                    self._append_history(uid, 'assistant', val_text)
                                    return val_text
                                # fallback
                                self._append_history(uid, 'user', user_message)
                                safe_data = self._force_in_character(str(data))
                                self._append_history(uid, 'assistant', safe_data)
                                return safe_data
                            except Exception:
                                text = self._force_in_character(text)
                                self._append_history(uid, 'user', user_message)
                                self._append_history(uid, 'assistant', text)
                                return text
                        else:
                            last_api_error = text or f"HTTP {resp.status}"
                            logger.debug(f"Kindroid send_message non-200 status {resp.status} for {url}: {text}")
                            if url.endswith('/send-message') and resp.status in (400, 401, 403, 429):
                                return f"Kindroid API error: {last_api_error}"
                except ClientError as e:
                    logger.warning(f"Kindroid request to {url} failed: {e}")

            logger.error("All Kindroid endpoints failed or returned non-200")
            if last_api_error:
                return f"Kindroid API error: {last_api_error}"
            return "Sorry, I couldn't reach Kindroid at the moment."

        except Exception as e:
            logger.error(f"Error communicating with Kindroid: {e}")
            return "Sorry, I encountered an error processing your message."

    async def get_character_info(self) -> dict:
        """Retrieve character information from local Ollama or remote Kindroid API"""
        try:
            # If local Ollama available, return model info
            if self.use_local_model and shutil.which('ollama'):
                try:
                    proc = await asyncio.create_subprocess_exec('ollama', 'ls', stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await proc.communicate()
                    if out:
                        text = out.decode('utf-8', errors='ignore')
                        lines = [l for l in text.splitlines() if l.strip()]
                        if len(lines) >= 2:
                            first = lines[1].split()[0]
                            return {'name': first, 'status': 'local'}
                except Exception as e:
                    logger.warning(f"Failed to query ollama models: {e}")

            # Fallback: HTTP request to remote Kindroid
            if not self.session:
                await self.initialize()

            headers = {
                'Authorization': f'Bearer {self.api_key}' if self.api_key else '',
                'Accept': 'application/json'
            }
            url = f"{self.api_base.rstrip('/')}/v1/characters/{self.character_code}"
            async with self.session.get(url, headers=headers, timeout=20) as resp:
                text = await resp.text()
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        return data if isinstance(data, dict) else {'raw': data}
                    except Exception:
                        return {'raw': text}

                logger.error(f"Kindroid get_character_info error status={resp.status}: {text}")
                return {'error': f'status_{resp.status}', 'detail': text}

        except Exception as e:
            logger.error(f"Error fetching character info: {e}")
            return {'error': 'exception', 'detail': str(e)}
