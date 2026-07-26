import asyncio, discord, os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
VIDEO = r"C:\Users\Andre Norris\kindroid-discord-bot\avatar\live\irene_live.mp4"

async def post():
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    async with client:
        @client.event
        async def on_ready():
            ch = discord.utils.find(
                lambda c: "irene" in c.name.lower() and isinstance(c, discord.TextChannel),
                client.get_all_channels()
            )
            if not ch:
                print("ERROR: No channel named irene found")
                await client.close()
                return
            print(f"Posting to #{ch.name} (ID {ch.id})")
            await ch.send(file=discord.File(VIDEO))
            print("Done.")
            await client.close()
        await client.start(TOKEN)

asyncio.run(post())
