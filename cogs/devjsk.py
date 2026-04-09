# cogs/owner.py - Revised DevJsk Command (Concise Single Text List, Owner-Only)
import discord
from discord.ext import commands

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="devjsk")
    @commands.is_owner()
    async def devjsk(self, ctx):
        """DevJsk: Quick list of Jishaku-like commands (Owner Only)."""
        content = """
**DevJsk Quick List**

**Tasks:**
tasks - List tasks. Ex: devjsk tasks
cancel <id> - Cancel task. Ex: devjsk cancel 1

**Python:**
py <code> - Run code. Ex: devjsk py print('Hi')
pyi <code> - Inspect output. Ex: devjsk pyi _bot
dis <code> - Disassemble. Ex: devjsk dis 'print(1)'
ast <code> - AST tree. Ex: devjsk ast 'if True: pass'
retain on/off - Toggle retention. Ex: devjsk retain on

**Shell:**
sh <cmd> - Run shell. Ex: devjsk sh

**Extensions:**
load <ext> - Load cog. Ex: devjsk load cogs.ping
reload <ext> - Reload. Ex: devjsk reload ~
unload <ext> - Unload. Ex: devjsk unload cogs.ping

**Utils:**
debug <cmd> - Time cmd. Ex: devjsk debug ping
repeat <n> <cmd> - Repeat. Ex: devjsk repeat 3 ping
exec <user> <cmd> - Impersonate. Ex: devjsk exec @me ban @bad
source <cmd> - Show source. Ex: devjsk source ping
rtt - Latency test. Ex: devjsk rtt
sync - Sync slashes. Ex: devjsk sync
permtrace #ch @role - Perms. Ex: devjsk permtrace #gen @mod
cat file.py - Read file. Ex: devjsk cat main.py
curl url - Fetch URL. Ex: devjsk curl https://meekly.vercel.app/

Run devjsk for list. Owner only!
        """
        await ctx.send(content)

async def setup(bot):
    await bot.add_cog(Owner(bot))