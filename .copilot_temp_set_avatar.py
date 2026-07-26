import os, subprocess, base64, json, sys
from pathlib import Path

BASE_DIR = Path.cwd()
input_mp4 = BASE_DIR / 'avatar' / 'live' / 'irene_live.mp4'
if not input_mp4.exists():
    print('ERROR: avatar clip not found at', input_mp4)
    sys.exit(2)

out_jpg = BASE_DIR / 'avatar' / 'live' / 'irene_avatar.jpg'
ffmpeg_path = BASE_DIR / 'ffmpeg' / 'bin' / 'ffmpeg.exe'
ffmpeg = str(ffmpeg_path) if ffmpeg_path.exists() else 'ffmpeg'

cmd = [ffmpeg, '-y', '-ss', '00:00:01', '-i', str(input_mp4), '-vframes', '1', '-vf', "scale=256:256:force_original_aspect_ratio=decrease,pad=256:256:(ow-iw)/2:(oh-ih)/2", '-q:v', '3', str(out_jpg)]
print('Running ffmpeg to extract frame...')
proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if proc.returncode != 0:
    print('ffmpeg failed:', proc.stderr.decode('utf-8', errors='ignore')[:1500])
    sys.exit(3)

print('Wrote image:', out_jpg, 'size=', out_jpg.stat().st_size)

# Load token from env or .env
token = os.getenv('DISCORD_TOKEN')
if not token:
    envf = BASE_DIR / '.env'
    if envf.exists():
        for line in envf.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith('DISCORD_TOKEN='):
                token = line.split('=',1)[1].strip()
                break

if not token:
    print('ERROR: DISCORD_TOKEN not found in environment or .env')
    sys.exit(4)

# Prepare payload
img_bytes = out_jpg.read_bytes()
# If image too large, try to re-encode smaller JPG via ffmpeg
if len(img_bytes) > 200000:
    small_jpg = BASE_DIR / 'avatar' / 'live' / 'irene_avatar_small.jpg'
    cmd2 = [ffmpeg, '-y', '-i', str(out_jpg), '-vf', 'scale=256:256', '-q:v', '5', str(small_jpg)]
    subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if small_jpg.exists():
        img_bytes = small_jpg.read_bytes()
        out_jpg = small_jpg

b64 = base64.b64encode(img_bytes).decode('ascii')
mime = 'image/jpeg'
payload = json.dumps({'avatar': f'data:{mime};base64,{b64}'}).encode('utf-8')

import urllib.request, urllib.error
req = urllib.request.Request('https://discord.com/api/v10/users/@me', data=payload, headers={
    'Authorization': f'Bot {token}',
    'Content-Type': 'application/json',
    'User-Agent': 'IreneBot/1.0'
}, method='PATCH')

print('Patching Discord profile...')
try:
    with urllib.request.urlopen(req) as resp:
        body = resp.read().decode('utf-8', errors='ignore')
        print('Discord response code:', resp.getcode())
        print(body[:1000])
        print('Avatar update successful')
except urllib.error.HTTPError as e:
    err = e.read().decode('utf-8', errors='ignore')
    print('HTTPError', e.code, err[:1500])
    sys.exit(5)
except Exception as e:
    print('Request failed:', str(e))
    sys.exit(6)