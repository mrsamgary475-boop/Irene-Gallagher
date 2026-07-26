# Kindroid Discord Bridge

A Discord bridge that brings your Kindroid character into Discord text and voice channels.

## Features

- ✅ **Hybrid Messaging**: Responds to mentions and replies in channels
- ✅ **Commands**: Use `!ask`, `!chat`, and bridge controls to interact
- ✅ **Character Integration**: Maintains your Kindroid character's personality
- ✅ **Conversation Memory**: Stores per-user Discord conversation memory
- ✅ **Voice Controls**: Join, speak, listen, and use automatic voice-clip fallback
- ✅ **Avatar Updates**: Optional mood-driven avatar clips
- ✅ **Async Processing**: Efficient message handling with Discord.py
- ✅ **Error Handling**: Robust error management and logging
- ✅ **Extensible**: Easy to add more features and commands

## Setup

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Kindroid Character Code and API Key

### Installation

1. **Clone or extract the project**
```bash
cd kindroid-discord-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
```

Edit `.env` and add:
- `DISCORD_TOKEN`: Your Discord bot token
- `KINDROID_CODE`: Your character code
- `KINDROID_API_KEY`: Your Kindroid API key
- `BOT_PREFIX`: Command prefix (default: `!`)
- `DISCORD_BOT_NICKNAME`: Server nickname to show (default: `Irene`)

Keep `.env` private. Never commit or paste either token or API key into a public channel.

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the token to your `.env` file as `DISCORD_TOKEN`
5. Enable these intents:
   - Message Content Intent
   - Server Members Intent
6. Go to OAuth2 → URL Generator
7. Select scopes: `bot`
8. Select permissions:
   - Send Messages
   - Read Messages/View Channels
   - Read Message History
9. Use the generated URL to invite bot to your server

For voice, also grant Connect, Speak, Use Voice Activity, and View Channel.

## Running the Bot

```bash
python main.py
```

The bot will start and connect to Discord. You'll see:
```
2026-07-24 01:40:00 - __main__ - INFO - Bot logged in as YourBot (ID: 1234567890)
2026-07-24 01:40:00 - __main__ - INFO - Kindroid client initialized
```

## Usage

### Via Mentions
```
@Kindroid How are you today?
```

### Via Commands
```
!ask What is the weather?
!chat Tell me a joke
!info Show bot information
!bridge_status
!memory
!forget
```

### Bridge reply modes

Use `!bridge_mode mentioned` for replies only when Irene is mentioned or replied to, `!bridge_mode all` for a dedicated bridge channel, or `!bridge_mode off` to disable automatic replies. Server managers can change this setting.

### Voice conversation

Join the same Discord voice channel as Irene and use the call panel's **Start Call** button. Irene listens through Discord's voice receive extension, sends a transcript to the text channel, and replies with TTS. If Discord rejects a voice session, the bot switches to voice MP3 clips in the text channel instead of retrying indefinitely.

For reliable voice input, use Discord's **voice message** button in the bridge text channel and send the recording. Irene transcribes it, replies as the character, and can attach a spoken reply without requiring live microphone capture. This works even when Discord rejects bot voice receive. Set `VOICE_MESSAGES_ENABLED=1` to enable it; in bridge mode, voice messages are accepted in the configured bridge channel automatically.

### Running without Discord

The local interface uses your Kindroid API credentials directly and does not require a Discord token or server. Copy `.env.example` to `.env`, keep `KINDROID_USE_LOCAL_MODEL=0`, then run:

```bat
local_launch.bat
```

Open `http://127.0.0.1:8765` if it does not open automatically. The page is a full-screen 16:9 call layout with the configured video avatar (`LOCAL_AVATAR_VIDEO`), camera picture-in-picture, Start/End Call controls, camera and mic controls, browser face/eye tracking, and local behavior reactions. When a face is detected, Irene receives short private context such as “looking at you,” “smiling,” or “looking away” with the next message, while the avatar framing and effects react immediately. The supplied `avatar/live/user_avatar.mp4` is used by default; remove that file or change the setting to use Irene's generated mood animation instead. Hold **Hold Talk** to record a voice turn. The browser sends the recording to the local app, which transcribes it, sends the text to Kindroid, and plays the configured TTS reply. The public Kindroid API currently returns text only; it does not expose Irene's exact in-app voice, so exact voice matching requires an official Kindroid audio endpoint or authorized voice asset.

### Windows desktop version

Run `windows_launch.bat` for the local Windows version. It opens Irene in Chrome or Edge, where the browser can install the interface as a desktop app from **Install app** or **Add to desktop**. Because it uses `localhost`, Windows browser camera and microphone permissions work without a certificate.

### Android phone version

The local interface is also an installable Android-friendly PWA; no API key is placed on the phone. The Windows PC runs the Kindroid connection and the Android phone acts as the call screen:

1. Connect the phone and PC to the same Wi-Fi network.
2. Run `android_launch.bat` on the PC.
3. Run `ipconfig`, find the PC's Wi-Fi IPv4 address, and open `http://PC-IP:8765` on the phone.
4. In Chrome, use **Add to Home screen** or **Install app**.

Text chat works over the local HTTP address. Android Chrome requires HTTPS for camera and microphone permissions and for PWA installation; configure a certificate trusted by the phone with `LOCAL_WEB_CERT_FILE` and `LOCAL_WEB_KEY_FILE` in `.env`, then open the matching `https://PC-IP:8765` address. Do not port-forward this service to the public internet because it is intended for a trusted local network.

If the phone cannot open the HTTP address, run PowerShell as Administrator once and allow the local server through Windows Firewall:

```powershell
New-NetFirewallRule -DisplayName "Irene local server 8765" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow -Profile Private
```

### Free neural avatar test

`LivePortrait_Colab_Free.ipynb` is a separate Google Colab test for animating Irene's photo with the official LivePortrait model. Upload the notebook to [Google Colab](https://colab.research.google.com/), choose a free GPU runtime if one is available, and run the cells in order. It produces a downloadable MP4; it does not replace the local real-time avatar. Free GPU access is limited and the photo is uploaded to the temporary Colab session.

### CPU-friendly local avatar

The local interface defaults to `LOCAL_AVATAR_MODE=cpu_lite`. This uses the browser's MediaPipe face landmarks, smoothed head pose, parallax, breathing, reaction movement, and audio energy instead of loading LivePortrait's multi-gigabyte neural weights. It is the mode intended for an i7-8700-class CPU and keeps the local app responsive. It is a lightweight approximation, not the proprietary Kindroid animation system.

### AI-generated 2.5D avatar asset

`Irene_2.5D_AI_Colab.ipynb` creates a more complete 2.5D asset using AI subject extraction, depth estimation, pose landmarks, an inpainted background, and separate torso, head, arm, and leg layers. Upload it to Google Colab, run the cells, download the ZIP, and extract its `irene_2p5d` folder to `avatar/live/`. The local app detects the required layers automatically and uses them instead of the flat photo. This is a generated layered asset, not full real-time LivePortrait.

### Sending SMS through your Assurance Wireless phone

The PWA cannot silently send SMS from a phone. The included `android_sms_relay` companion app uses the phone's own SIM after you grant Android's SMS permission:

1. Set `SMS_DEVICE_TOKEN` in `.env` to a private random value. In PowerShell, generate one with `-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 40 | ForEach-Object {[char]$_})`.
2. Install the prebuilt `IreneSmsRelay-debug.apk` from the project folder, or open `android_sms_relay` in Android Studio and build it yourself.
3. Start `android_launch.bat` on Windows and enter the PC URL, the same device token, and your Assurance Wireless cellphone number in the app.
4. Leave the relay running with its notification visible.
5. Check **Text me** before sending a message to have that Irene reply delivered as SMS.

SMS messages are queued only while the local PC app is running and are sent through your normal mobile plan. Keep the PC and phone on the same trusted Wi-Fi network; never port-forward the relay endpoints.

### In Threads
Reply to bot messages in threads to continue conversations

## Project Structure

```
kindroid-discord-bot/
├── main.py              # Bot entry point
├── config.py            # Configuration management
├── kindroid_client.py   # Kindroid API client
├── cogs/
│   ├── __init__.py
│   ├── commands.py      # Command handlers
│   └── messages.py      # Message event handlers
├── requirements.txt     # Python dependencies
├── .env.example        # Environment template
└── README.md           # This file
```

## Configuration

All settings are managed in `config.py` and `.env`:

- `DISCORD_TOKEN`: Your Discord bot token
- `BOT_PREFIX`: Command prefix (e.g., `!`)
- `KINDROID_CODE`: Character identifier
- `KINDROID_API_KEY`: API authentication
- `KINDROID_API_BASE`: API endpoint (default: https://api.kindroid.ai)
- `KINDROID_VOICE_REFERENCE`: local MP3 reference for Irene's authorized voice asset
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)
- `KINDROID_BRIDGE_MODE`: `1` to enable dedicated Kindroid bridge behavior in server channels
- `KINDROID_BRIDGE_CHANNEL_IDS`: optional comma-separated channel IDs; when set, bridge replies only in those channels
- `KINDROID_MEMORY_TURNS`: maximum remembered turns per user (default: 20)
- `VOICE_MESSAGES_ENABLED`: transcribe Discord voice messages in text channels (`1` by default)
- `TTS_ENGINE`: `edge` (default) or `gtts`
- `TTS_VOICE`: Edge TTS voice name (default: `en-US-AriaNeural`)

## Troubleshooting

### Bot not responding
1. Check DISCORD_TOKEN is correct in `.env`
2. Verify bot has message permissions in server
3. Check bot intents are enabled in Developer Portal
4. Review logs for error messages
5. If logs say "online but not in any Discord server", the bot is not invited yet. Generate an OAuth2 invite URL and add it to your server.

### Kindroid integration not working
1. Verify KINDROID_API_KEY is set
2. Check KINDROID_CODE matches your character
3. Ensure Kindroid API is accessible
4. Check network connectivity

### Permission errors
1. Verify bot has "Send Messages" permission
2. Check bot role position in server hierarchy
3. Ensure bot can read message history

## Development

### Adding New Commands

Edit `cogs/commands.py` and add:
```python
@commands.command(name='yourcommand')
async def your_command(self, ctx, *, args: str):
    """Your command description"""
    async with ctx.typing():
        response = await self.kindroid.send_message(args)
        await ctx.send(response)
```

### Adding Event Handlers

Edit `cogs/messages.py` to add new message event handlers or create new cog files.

### Extending Kindroid Client

Edit `kindroid_client.py` to add more Kindroid API methods as needed.

## Support

For issues or questions:
1. Check the logs in the console output
2. Review Discord Developer Portal bot settings
3. Verify Kindroid API credentials
4. Check project README for common issues

## License

This project is provided as-is for personal use.

---

**Bot is now ready to interact with Discord users while maintaining your Kindroid character's personality!**
