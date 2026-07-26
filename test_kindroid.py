import asyncio
from kindroid_client import KindroidClient
import json
import os

async def main():
    client = KindroidClient()
    await client.initialize()
    resp = await client.send_message("Hello, this is a test from local script.", user_id="test-user")
    print("=== RESPONSE ===")
    print(resp)
    await client.close()

    memfile = os.path.join(os.getcwd(), 'conversations.json')
    print("\n=== MEMORY FILE CONTENT ===")
    if os.path.exists(memfile):
        with open(memfile, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception as e:
                print('Failed to read memory file:', e)
    else:
        print('No memory file found')

if __name__ == '__main__':
    asyncio.run(main())
