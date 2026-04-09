import discord
from discord.ext import commands
import aiosqlite
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from main import DEV_ID, CORE_DB

# Role → emoji mapping (your custom emojis)
from emojis import ROLE_EMOJIS


class DeveloperReact(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # === Restrict commands to developer only ===
    def dev_only():
        async def predicate(ctx):
            if ctx.author.id != DEV_ID:
                await ctx.send("❌ Only the developer can use this command.")
                return False
            return True
        return commands.check(predicate)

    # === Listener for mentions ===
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        mentioned_ids = [u.id for u in message.mentions]
        if not mentioned_ids:
            return

        async with aiosqlite.connect(CORE_DB) as db:
            async with db.execute("SELECT user_id, role FROM devreact WHERE user_id IN ({})".format(','.join(['?']*len(mentioned_ids))), mentioned_ids) as cursor:
                rows = await cursor.fetchall()
        
        # Group roles by user_id
        user_roles = {}
        for uid, role in rows:
            user_roles.setdefault(uid, []).append(role)

        for uid, roles in user_roles.items():
            for role in roles:
                emoji = ROLE_EMOJIS.get(role)
                if emoji:
                    try:
                        await message.add_reaction(emoji)
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass

    # === Command group ===
    @commands.group(name="devreact", invoke_without_command=True)
    @dev_only()
    async def devreact(self, ctx):
        await ctx.send("⚙️ Usage: `devreact add/remove/list`")

    @devreact.command(name="add")
    @dev_only()
    async def add(self, ctx, user: discord.User, role: str):
        """Add a role to a user"""
        role = role.capitalize()
        if role not in ROLE_EMOJIS:
            return await ctx.send(f"❌ Invalid role. Use: {', '.join(ROLE_EMOJIS.keys())}")

        async with aiosqlite.connect(CORE_DB) as db:
            await db.execute("INSERT OR IGNORE INTO devreact (user_id, role) VALUES (?, ?)", (user.id, role))
            await db.commit()

        await ctx.send(f"✅ Added **{role}** to **{user}** → {ROLE_EMOJIS[role]}")

    @devreact.command(name="remove")
    @dev_only()
    async def remove(self, ctx, user: discord.User, role: str = None):
        """Remove a specific role or all roles from a user"""
        async with aiosqlite.connect(CORE_DB) as db:
            if role:
                role = role.capitalize()
                await db.execute("DELETE FROM devreact WHERE user_id = ? AND role = ?", (user.id, role))
            else:
                await db.execute("DELETE FROM devreact WHERE user_id = ?", (user.id,))
            await db.commit()
        
        if role:
            await ctx.send(f"🗑️ Removed **{role}** from **{user}**")
        else:
            await ctx.send(f"🗑️ Removed **all roles** from **{user}**")

    @devreact.command(name="list")
    @dev_only()
    async def list(self, ctx):
        async with aiosqlite.connect(CORE_DB) as db:
            async with db.execute("SELECT user_id, role FROM devreact") as cursor:
                rows = await cursor.fetchall()
        
        if not rows:
            return await ctx.send("📭 No users saved.")

        db_grouped = {}
        for uid, role in rows:
            db_grouped.setdefault(uid, []).append(role)

        msg = "👥 **DevReact List**\n"
        for uid, roles in db_grouped.items():
            user = self.bot.get_user(uid) or f"<@{uid}>"
            emojis = " ".join([ROLE_EMOJIS.get(r, "❓") for r in roles])
            msg += f"- {user} ({uid}) → {', '.join(roles)} {emojis}\n"

        await ctx.send(msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(DeveloperReact(bot))

