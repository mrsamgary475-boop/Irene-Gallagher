import discord
from discord.ext import commands
import logging
import sys
import os
import msvcrt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)
from config import DISCORD_TOKEN, COMMAND_PREFIX, LOG_LEVEL, DISCORD_SERVER_TAG, DISCORD_BOT_NICKNAME
from kindroid_client import KindroidClient

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Create bot instance
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Initialize Kindroid client
kindroid_client = KindroidClient()
bot.kindroid_client = kindroid_client
_INSTANCE_LOCK = None


def _acquire_instance_lock():
    """Allow only one bot process per workspace on Windows."""
    lock_path = BASE_DIR / "bot.lock"
    lock_file = open(lock_path, "a+")
    try:
        lock_file.seek(0)
        lock_file.write("\0")
        lock_file.flush()
        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        return lock_file
    except OSError:
        lock_file.close()
        return None


def _release_instance_lock(lock_file):
    if not lock_file:
        return
    try:
        lock_file.seek(0)
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    lock_file.close()


@bot.event
async def on_ready():
    """Called when bot is ready"""
    logger.info(f'Bot logged in as {bot.user} (ID: {bot.user.id})')
    if not bot.guilds:
        logger.warning("Bot is online but not in any Discord server yet. Invite it from the Discord Developer Portal (OAuth2 URL Generator).")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"messages | {COMMAND_PREFIX}help"
        )
    )
    await _clear_stale_voice_state()
    await _apply_server_tag()


async def _apply_server_tag():
    tag = (DISCORD_SERVER_TAG or "").strip()
    nickname = (DISCORD_BOT_NICKNAME or "").strip()
    if not tag and not nickname:
        return
    for guild in bot.guilds:
        try:
            me = guild.me or guild.get_member(bot.user.id)
            if not me:
                continue
            current_name = (me.nick or bot.user.name or "Irene").strip()
            clean_base = current_name.split("[", 1)[0].strip()
            desired_base = (nickname or clean_base or "Irene").strip()
            tagged_name = f"{desired_base} [{tag}]" if tag else desired_base
            if me.nick == tagged_name:
                continue
            await me.edit(nick=tagged_name, reason="Apply configured server tag")
        except discord.Forbidden:
            logger.warning("Missing permission to set nickname in guild %s", guild.id)
        except Exception as exc:
            logger.warning("Failed to apply server tag in guild %s: %s", guild.id, exc)


async def _clear_stale_voice_state():
    """On startup, clear any lingering voice state from the previous session (prevents 4006)."""
    for guild in bot.guilds:
        try:
            me = guild.me
            if me and me.voice:
                logger.info("Clearing stale voice state in guild %s", guild.id)
                await guild.change_voice_state(channel=None)
        except Exception as exc:
            logger.warning("Failed to clear voice state in guild %s: %s", guild.id, exc)


@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"Command not found. Use `{COMMAND_PREFIX}help` for available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument. Use `{COMMAND_PREFIX}help {ctx.command}` for help.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("An error occurred while processing your command.")


async def load_cogs():
    """Load all cogs from the cogs directory"""
    cogs_path = BASE_DIR / 'cogs'
    
    for cog_file in cogs_path.glob('*.py'):
        if cog_file.name.startswith('_'):
            continue
        
        cog_name = f'cogs.{cog_file.stem}'
        try:
            await bot.load_extension(cog_name)
            logger.info(f'Loaded cog: {cog_name}')
        except Exception as e:
            logger.error(f'Failed to load cog {cog_name}: {e}')


async def main():
    """Main bot startup function"""
    global _INSTANCE_LOCK
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set in .env file")
        sys.exit(1)

    _INSTANCE_LOCK = _acquire_instance_lock()
    if not _INSTANCE_LOCK:
        logger.error("Another Irene bot instance is already running in this folder.")
        sys.exit(1)
    
    try:
        # Initialize Kindroid client
        await kindroid_client.initialize()
        logger.info("Kindroid client initialized")
        
        # Load cogs
        await load_cogs()
        
        # Start bot
        logger.info("Starting Discord bot...")
        async with bot:
            await bot.start(DISCORD_TOKEN)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        _release_instance_lock(_INSTANCE_LOCK)
        await kindroid_client.close()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
