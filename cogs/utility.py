import discord
from discord.ext import commands, tasks
from discord import ui
from typing import Optional
import requests
from io import BytesIO
import aiosqlite
import os
import time
import re

# ================= CONFIG =================
DB_PATH = "db/utility.db"

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import (
    CHECK as EMOJI_CHECK,
    CROSS as EMOJI_CROSS,
    TIMER as EMOJI_TIMER,
    REPLY as EMOJI_REPLY,
    BELL as EMOJI_BELL
)


# ================= UI HELPER =================
async def ui_message(ctx, title: str, text: str):
    view = ui.LayoutView(timeout=120)
    view.add_item(
        ui.Container(
            ui.TextDisplay(f"# {title}"),
            ui.Separator(),
            ui.TextDisplay(text)
        )
    )
    await ctx.send(view=view)


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        os.makedirs("db", exist_ok=True)
        bot.loop.create_task(self._startup())

    async def _startup(self):
        await self._init_db()
        self.timer_loop.start()

    # ================= DATABASE =================
    async def _init_db(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS timers (
                channel INTEGER,
                user INTEGER,
                end INTEGER
            );

            CREATE TABLE IF NOT EXISTS autoresponders (
                guild INTEGER,
                trigger TEXT,
                response TEXT
            );

            CREATE TABLE IF NOT EXISTS autoreacts (
                guild INTEGER,
                trigger TEXT,
                emoji TEXT
            );
            """)
            await db.commit()

    # ================= AVATAR / BANNER =================
    async def _send_media(self, ctx, user, asset: discord.Asset, title: str):
        fmt = "gif" if asset.is_animated() else "png"
        filename = f"{title.lower()}.{fmt}"

        data = BytesIO(
            requests.get(asset.replace(size=1024, format=fmt).url).content
        )

        gallery = ui.MediaGallery()
        gallery.add_item(media=f"attachment://{filename}")

        buttons = [
            ui.Button(label="PNG", url=asset.replace(size=1024, format="png").url),
            ui.Button(label="JPG", url=asset.replace(size=1024, format="jpg").url),
            ui.Button(label="WEBP", url=asset.replace(size=1024, format="webp").url),
        ]
        if asset.is_animated():
            buttons.append(
                ui.Button(label="GIF", url=asset.replace(size=1024, format="gif").url)
            )

        view = ui.LayoutView(timeout=120)
        view.add_item(
            ui.Container(
                ui.TextDisplay(f"# {user.name}'s {title}"),
                ui.Separator(),
                gallery,
                ui.Separator(),
                ui.ActionRow(*buttons)
            )
        )

        await ctx.send(view=view, files=[discord.File(data, filename)])

    @commands.command(name="avatar", aliases=["av", "pfp"])
    async def avatar(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        await self._send_media(ctx, member, member.display_avatar, "Avatar")

    @commands.command(name="banner")
    async def banner(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)

        if not user.banner:
            return await ui_message(ctx, "Banner", f"{EMOJI_CROSS} User has no banner")

        await self._send_media(ctx, user, user.banner, "Banner")

    # ================= TIMER =================
    @commands.command(name="timer")
    async def timer(self, ctx, seconds: int):
        if seconds <= 0:
            return await ui_message(ctx, "Timer", f"{EMOJI_CROSS} Invalid time")

        end = int(time.time()) + seconds
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO timers VALUES (?, ?, ?)",
                (ctx.channel.id, ctx.author.id, end)
            )
            await db.commit()

        await ui_message(ctx, "Timer Started", f"{EMOJI_TIMER} Ends <t:{end}:R>")

    @tasks.loop(seconds=5)
    async def timer_loop(self):
        now = int(time.time())
        async with aiosqlite.connect(DB_PATH) as db:
            rows = await db.execute_fetchall(
                "SELECT rowid, channel, user FROM timers WHERE end<=?",
                (now,)
            )

            for rid, ch, uid in rows:
                channel = self.bot.get_channel(ch)
                if channel:
                    await channel.send(f"{EMOJI_TIMER} <@{uid}> your timer ended")
                await db.execute("DELETE FROM timers WHERE rowid=?", (rid,))
            await db.commit()

    # ================= AUTORESPONDER COMMANDS =================
    @commands.group(name="ar", invoke_without_command=True)
    async def ar(self, ctx):
        await ui_message(
            ctx,
            "Autoresponder",
            "`ar add <word> <reply>`\n`ar remove <word>`\n`ar list`"
        )

    @ar.command(name="add")
    @commands.has_permissions(manage_messages=True)
    async def ar_add(self, ctx, trigger: str, *, response: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO autoresponders VALUES (?, ?, ?)",
                (ctx.guild.id, trigger.lower(), response)
            )
            await db.commit()

        await ui_message(ctx, "Autoresponder", f"{EMOJI_CHECK} Added `{trigger}`")

    @ar.command(name="remove")
    @commands.has_permissions(manage_messages=True)
    async def ar_remove(self, ctx, trigger: str):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "DELETE FROM autoresponders WHERE guild=? AND trigger=?",
                (ctx.guild.id, trigger.lower())
            )
            await db.commit()

        await ui_message(
            ctx,
            "Autoresponder",
            f"{EMOJI_CHECK} Removed `{trigger}`"
            if cur.rowcount else f"{EMOJI_CROSS} Trigger not found"
        )

    @ar.command(name="list")
    async def ar_list(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            rows = await db.execute_fetchall(
                "SELECT trigger, response FROM autoresponders WHERE guild=?",
                (ctx.guild.id,)
            )

        if not rows:
            return await ui_message(ctx, "Autoresponder", f"{EMOJI_CROSS} None set")

        await ui_message(
            ctx,
            "Autoresponders",
            "\n".join(f"`{t}` → {r}" for t, r in rows)
        )

    # ================= AUTOREACT COMMANDS =================
    @commands.group(name="react", invoke_without_command=True)
    async def react(self, ctx):
        await ui_message(
            ctx,
            "Autoreact",
            "`react add <word | @user | @role> <emoji>`\n`react remove <trigger>`\n`react list`"
        )

    @react.command(name="add")
    @commands.has_permissions(manage_messages=True)
    async def react_add(self, ctx, trigger: str, emoji: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO autoreacts VALUES (?, ?, ?)",
                (ctx.guild.id, trigger.lower(), emoji)
            )
            await db.commit()

        await ui_message(ctx, "Autoreact", f"{EMOJI_CHECK} Added `{trigger}` → {emoji}")

    @react.command(name="remove")
    @commands.has_permissions(manage_messages=True)
    async def react_remove(self, ctx, trigger: str):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "DELETE FROM autoreacts WHERE guild=? AND trigger=?",
                (ctx.guild.id, trigger.lower())
            )
            await db.commit()

        await ui_message(
            ctx,
            "Autoreact",
            f"{EMOJI_CHECK} Removed `{trigger}`"
            if cur.rowcount else f"{EMOJI_CROSS} Trigger not found"
        )

    @react.command(name="list")
    async def react_list(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            rows = await db.execute_fetchall(
                "SELECT trigger, emoji FROM autoreacts WHERE guild=?",
                (ctx.guild.id,)
            )

        if not rows:
            return await ui_message(ctx, "Autoreact", f"{EMOJI_CROSS} None set")

        await ui_message(
            ctx,
            "Autoreacts",
            "\n".join(f"`{t}` → {e}" for t, e in rows)
        )

    # ================= LISTENER =================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.guild:
            content = message.content.lower()
            words = re.findall(r"\b\w+\b", content)

            async with aiosqlite.connect(DB_PATH) as db:
                ars = await db.execute_fetchall(
                    "SELECT trigger, response FROM autoresponders WHERE guild=?",
                    (message.guild.id,)
                )
                reacts = await db.execute_fetchall(
                    "SELECT trigger, emoji FROM autoreacts WHERE guild=?",
                    (message.guild.id,)
                )

            # EXACT autoresponder
            for t, r in ars:
                if content.strip() == t:
                    await message.reply(f"{EMOJI_REPLY} {r}")
                    break

            # WORD / MENTION autoreact
            for t, e in reacts:
                if (
                    t in words or
                    any(t == f"<@{m.id}>" or t == f"<@!{m.id}>" for m in message.mentions) or
                    any(t == f"<@&{r.id}>" for r in message.role_mentions)
                ):
                    try:
                        await message.add_reaction(e)
                    except:
                        pass
                    break

       # await self.bot.process_commands(message)


async def setup(bot):
    await bot.add_cog(Utility(bot))
