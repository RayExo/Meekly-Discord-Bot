import os
import sqlite3
import asyncio
import time
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv
import aiosqlite

# =========================
# LOAD ENV
# =========================
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not found in .env file")

# =========================
# BASIC CONFIG
# =========================
OWNER_ID = 870179991462236170
DEV_ID = 870179991462236170
DEVELOPER_IDS = [870179991462236170]
DEFAULT_PREFIX = "+"

CORE_DB = Path("db/core.db")
PREMIUM_DB = Path("db/premium.db")
TRACKER_DB = Path("db/tracker.db")

COGS_DIR = Path("cogs")
EVENTS_DIR = Path("events")
AUTOMOD_DIR = Path("automod")
ANTINUKE_DIR = Path("antinuke")

# =========================
# PREMIUM CONFIG
# =========================
SUPPORT_LINK = "https://discord.gg/codexdev"
INVITE_LINK = "https://discord.com/oauth2/authorize?client_id=1409860321295732808&scope=bot&permissions=8"
VOTE_LINK = "https://top.gg/bot/1409860321295732808/vote"
SUPPORT_SERVER = SUPPORT_LINK
BOOSTS_REQUIRED = 1
LOCKED_COGS = ("ChangeAvatar", "ChangeBanner", "ChangeBio")

# =========================
# CUSTOM EMOJIS
# =========================
from emojis import EMOJIES

# =========================
# BOT SETUP
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True
intents.members = True

async def get_prefix(bot, message):
    if not message or not message.guild:
        return DEFAULT_PREFIX
    async with aiosqlite.connect(CORE_DB) as db:
        async with db.execute("SELECT prefix FROM prefixes WHERE guild_id = ?", (message.guild.id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else DEFAULT_PREFIX

bot = commands.Bot(
    command_prefix=get_prefix,
    owner_id=OWNER_ID,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# Attach Global Links
bot.support_link = SUPPORT_LINK
bot.invite_link = INVITE_LINK
bot.vote_link = VOTE_LINK

# =========================
# 🔒 GLOBAL PREMIUM LOCK
# =========================
@bot.check
async def premium_global_lock(ctx: commands.Context):
    if not ctx.guild or not ctx.command:
        return True

    if ctx.command.cog_name not in LOCKED_COGS:
        return True

    uid = ctx.author.id
    gid = ctx.guild.id

    async with aiosqlite.connect(PREMIUM_DB) as db:
        # Check user premium
        async with db.execute("SELECT expires FROM premium_users WHERE user_id = ?", (uid,)) as cursor:
            premium_row = await cursor.fetchone()
        
        # Check guild boosts
        async with db.execute("SELECT total_boosts FROM guild_boosts WHERE guild_id = ?", (gid,)) as cursor:
            boost_row = await cursor.fetchone()
    
    boosts = boost_row[0] if boost_row else 0
    prefix = await get_prefix(bot, ctx.message)

    # 🔹 NO PREMIUM
    if not premium_row:
        await ctx.send(
            f"{EMOJIES['lock']} **Premium Not Active in this Server**\n\n"
            f"{EMOJIES['boost']} **Server Boosts:** `{boosts}/{BOOSTS_REQUIRED}`\n"
            f"{EMOJIES['info']} Boost this server **{BOOSTS_REQUIRED} times**\n"
            f"`{prefix}boost`"
        )
        return False

    # 🔹 PREMIUM EXPIRED
    if premium_row[0] <= time.time():
        await ctx.send(
            f"{EMOJIES['cross']} **Premium Expired**\n\n"
            f"{EMOJIES['cart']} Renew Premium to continue using boosts"
        )
        return False

    # 🔹 SERVER NOT BOOSTED
    if boosts < BOOSTS_REQUIRED:
        await ctx.send(
            f"{EMOJIES['lock']} **Premium Not Active in this Server**\n\n"
            f"{EMOJIES['boost']} **Server Boosts:** `{boosts}/{BOOSTS_REQUIRED}`\n"
            f"{EMOJIES['info']} Use `{prefix}boost` to unlock"
        )
        return False

    return True

# =========================
# DB INITIALIZER
# =========================
async def init_databases():
    Path("db").mkdir(exist_ok=True)
    
    async with aiosqlite.connect(CORE_DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS prefixes (guild_id INTEGER PRIMARY KEY, prefix TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS devreact (user_id INTEGER, role TEXT, PRIMARY KEY (user_id, role))")
        await db.execute("CREATE TABLE IF NOT EXISTS noprefix (user_id INTEGER PRIMARY KEY, plan TEXT, added_by INTEGER, added_at TEXT, expires TEXT)")
        await db.commit()
    
    async with aiosqlite.connect(PREMIUM_DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS premium_users (user_id INTEGER PRIMARY KEY, plan TEXT, expires INTEGER, boosts INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS user_boosts (user_id INTEGER, guild_id INTEGER, amount INTEGER, PRIMARY KEY (user_id, guild_id))")
        await db.execute("CREATE TABLE IF NOT EXISTS guild_boosts (guild_id INTEGER PRIMARY KEY, total_boosts INTEGER)")
        await db.commit()

    async with aiosqlite.connect(TRACKER_DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS messages (guild_id INTEGER, user_id INTEGER, message_count INTEGER DEFAULT 0, daily_count INTEGER DEFAULT 0, PRIMARY KEY (guild_id, user_id))")
        await db.execute("CREATE TABLE IF NOT EXISTS blacklisted_channels (guild_id INTEGER, channel_id INTEGER, PRIMARY KEY (guild_id, channel_id))")
        await db.commit()

# =========================
# STATUS LOOP
# =========================
async def update_status():
    while True:
        g = len(bot.guilds)
        await bot.change_presence(
            status=discord.Status.idle,
            activity=discord.CustomActivity(name=f"Looking {g/1000:.3f}K Servers")
        )
        await asyncio.sleep(300)

# =========================
# READY EVENT
# =========================
@bot.event
async def on_ready():
    print("=" * 55)
    print(f"🤖 Logged in as: {bot.user}")
    print(f"📚 Commands Loaded: {len(bot.commands)}")
    print(f"🧩 Cogs Loaded: {len(bot.cogs)}")
    print("🚀 BOT IS FULLY READY")
    print("=" * 55)
    asyncio.create_task(update_status())

# =========================
# PREFIX COMMANDS
# =========================
@bot.command()
@commands.has_permissions(administrator=True)
async def setprefix(ctx, prefix: str):
    if not prefix or len(prefix) > 10:
        return await ctx.send(f"{EMOJIES['cross']} Prefix must be 1–10 characters")
    
    async with aiosqlite.connect(CORE_DB) as db:
        await db.execute("INSERT OR REPLACE INTO prefixes (guild_id, prefix) VALUES (?, ?)", (ctx.guild.id, prefix))
        await db.commit()
    await ctx.send(f"{EMOJIES['check']} Prefix set to `{prefix}`")

@bot.command()
@commands.has_permissions(administrator=True)
async def resetprefix(ctx):
    async with aiosqlite.connect(CORE_DB) as db:
        await db.execute("DELETE FROM prefixes WHERE guild_id = ?", (ctx.guild.id,))
        await db.commit()
    await ctx.send(f"{EMOJIES['check']} Prefix reset to `{DEFAULT_PREFIX}`")

# =========================
# LOADERS (VERBOSE)
# =========================
async def load_folder(folder: Path, label: str):
    folder.mkdir(exist_ok=True)
    ok = fail = 0
    for file in folder.glob("*.py"):
        if file.name.startswith("_"):
            continue
        ext = f"{folder.name}.{file.stem}"
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded {label}: {ext}")
            ok += 1
        except Exception as e:
            print(f"❌ Failed {label}: {ext}\n   ↳ {e}")
            fail += 1
    print(f"📦 {label} Loaded: {ok} | Failed: {fail}\n")

async def load_jishaku_ext():
    try:
        await bot.load_extension("jishaku")
        print("✅ Jishaku Loaded (Owner Only)\n")
    except Exception as e:
        print(f"❌ Jishaku Failed: {e}\n")

# =========================
# MAIN
# =========================
async def main():
    await init_databases()
    async with bot:
        # os.system("clear") # Removed for windows compatibility issues if any, though it worked before
        await load_folder(COGS_DIR, "Cogs")
        await load_folder(EVENTS_DIR, "Events")
        await load_folder(AUTOMOD_DIR, "Automod")
        await load_folder(ANTINUKE_DIR, "AntiNuke")
        await load_jishaku_ext()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

