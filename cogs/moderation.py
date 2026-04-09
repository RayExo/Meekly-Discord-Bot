import discord
from discord.ext import commands
import sys
from pathlib import Path

# Add parent directory to path to import main config
sys.path.insert(0, str(Path(__file__).parent.parent))
from emojis import CHECK, CROSS

# Custom Emojis
SUCCESS_EMOJI = CHECK
FAIL_EMOJI = CROSS

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------- WARN ----------------
    @commands.command(name="warn")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member = None, *, reason=None):
        if not member:
            return await ctx.send(f"{FAIL_EMOJI} Please provide a user to warn.")
        if member == ctx.author:
            return await ctx.send(f"{FAIL_EMOJI} You cannot warn yourself.")
        if member.id == ctx.guild.owner_id:
            return await ctx.send(f"{FAIL_EMOJI} You cannot warn the server owner.")

        if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role <= member.top_role:
            return await ctx.send(f"{FAIL_EMOJI} You cannot warn someone with an equal or higher role.")

        try:
            await member.send(
                f"You have been warned in **{ctx.guild.name}** by **{ctx.author}**.\nReason: {reason or 'No reason provided'}"
            )
        except discord.Forbidden:
            pass

        await ctx.send(f"{SUCCESS_EMOJI} {member} has been warned. Reason: {reason or 'No reason provided'}")

    # ---------------- BAN ----------------
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, *, reason=None):
        if not member:
            return await ctx.send(f"{FAIL_EMOJI} Please provide a user to ban.")
        if member == ctx.author:
            return await ctx.send(f"{FAIL_EMOJI} You cannot ban yourself.")
        if member.id == ctx.guild.owner_id:
            return await ctx.send(f"{FAIL_EMOJI} You cannot ban the server owner.")

        if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role <= member.top_role:
            return await ctx.send(f"{FAIL_EMOJI} You cannot ban someone with an equal or higher role.")
        if ctx.guild.me.top_role <= member.top_role:
            return await ctx.send(f"{FAIL_EMOJI} My role is not high enough to ban that member.")

        try:
            await member.ban(reason=reason or f"Action by {ctx.author}")
            await ctx.send(f"{SUCCESS_EMOJI} {member} has been banned. Reason: {reason or 'No reason provided'}")
        except Exception as e:
            await ctx.send(f"{FAIL_EMOJI} Failed to ban: {e}")

    # ---------------- UNBAN ----------------
    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int = None, *, reason=None):
        if not user_id:
            return await ctx.send(f"{FAIL_EMOJI} Provide a user ID to unban.")

        try:
            banned_users = await ctx.guild.bans()
            user = discord.utils.get(banned_users, user=lambda u: u.user.id == user_id)
            if not user:
                return await ctx.send(f"{FAIL_EMOJI} That user is not banned.")
            await ctx.guild.unban(user.user, reason=reason or f"Action by {ctx.author}")
            await ctx.send(f"{SUCCESS_EMOJI} {user.user} has been unbanned. Reason: {reason or 'No reason provided'}")
        except Exception as e:
            await ctx.send(f"{FAIL_EMOJI} Failed to unban: {e}")

    # ---------------- KICK ----------------
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, *, reason=None):
        if not member:
            return await ctx.send(f"{FAIL_EMOJI} Provide a user to kick.")
        if member == ctx.author:
            return await ctx.send(f"{FAIL_EMOJI} You cannot kick yourself.")
        if member.id == ctx.guild.owner_id:
            return await ctx.send(f"{FAIL_EMOJI} You cannot kick the server owner.")

        if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role <= member.top_role:
            return await ctx.send(f"{FAIL_EMOJI} You cannot kick someone with an equal or higher role.")
        if ctx.guild.me.top_role <= member.top_role:
            return await ctx.send(f"{FAIL_EMOJI} My role is not high enough to kick that member.")

        try:
            await member.kick(reason=reason or f"Action by {ctx.author}")
            await ctx.send(f"{SUCCESS_EMOJI} {member} has been kicked. Reason: {reason or 'No reason provided'}")
        except Exception as e:
            await ctx.send(f"{FAIL_EMOJI} Failed to kick: {e}")

    # ---------------- MUTE ----------------
    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member = None, *, reason=None):
        if not member:
            return await ctx.send(f"{FAIL_EMOJI} Provide a user to mute.")
        if member == ctx.author:
            return await ctx.send(f"{FAIL_EMOJI} You cannot mute yourself.")
        if member.id == ctx.guild.owner_id:
            return await ctx.send(f"{FAIL_EMOJI} You cannot mute the server owner.")

        if ctx.author.id != ctx.guild.owner_id and ctx.author.top_role <= member.top_role:
            return await ctx.send(f"{FAIL_EMOJI} You cannot mute someone with an equal or higher role.")
        if ctx.guild.me.top_role <= member.top_role:
            return await ctx.send(f"{FAIL_EMOJI} My role is not high enough to mute that member.")

        if member.timed_out_until and member.timed_out_until > discord.utils.utcnow():
            return await ctx.send(f"{FAIL_EMOJI} {member} is already muted.")

        try:
            await member.timeout(None, reason=reason or f"Action by {ctx.author}")  # indefinite mute
            await ctx.send(f"{SUCCESS_EMOJI} {member} has been muted. Reason: {reason or 'No reason provided'}")
        except Exception as e:
            await ctx.send(f"{FAIL_EMOJI} Failed to mute: {e}")

    # ---------------- UNMUTE ----------------
    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member = None, *, reason=None):
        if not member:
            return await ctx.send(f"{FAIL_EMOJI} Provide a user to unmute.")

        if not member.timed_out_until or member.timed_out_until < discord.utils.utcnow():
            return await ctx.send(f"{FAIL_EMOJI} {member} is not muted.")

        try:
            await member.timeout(None)
            await ctx.send(f"{SUCCESS_EMOJI} {member} has been unmuted. Reason: {reason or 'No reason provided'}")
        except Exception as e:
            await ctx.send(f"{FAIL_EMOJI} Failed to unmute: {e}")

    # ---------------- LOCK ----------------
    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is False:
            return await ctx.send(f"{FAIL_EMOJI} Channel is already locked.")

        overwrite.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"{SUCCESS_EMOJI} Channel locked by {ctx.author.mention}")

    # ---------------- UNLOCK ----------------
    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is None or overwrite.send_messages is True:
            return await ctx.send(f"{FAIL_EMOJI} Channel is not locked.")

        overwrite.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"{SUCCESS_EMOJI} Channel unlocked by {ctx.author.mention}")

    # ---------------- HIDE ----------------
    @commands.command(name="hide")
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.view_channel is False:
            return await ctx.send(f"{FAIL_EMOJI} Channel is already hidden.")

        overwrite.view_channel = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"{SUCCESS_EMOJI} Channel hidden by {ctx.author.mention}")

    # ---------------- UNHIDE ----------------
    @commands.command(name="unhide")
    @commands.has_permissions(manage_channels=True)
    async def unhide(self, ctx):
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        if overwrite.view_channel is None or overwrite.view_channel is True:
            return await ctx.send(f"{FAIL_EMOJI} Channel is not hidden.")

        overwrite.view_channel = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"{SUCCESS_EMOJI} Channel unhidden by {ctx.author.mention}")

    # ---------------- ERROR HANDLER ----------------
    @ban.error
    @kick.error
    @mute.error
    @unmute.error
    @unban.error
    @warn.error
    @lock.error
    @unlock.error
    @hide.error
    @unhide.error
    async def mod_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(f"{FAIL_EMOJI} You lack permissions for this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"{FAIL_EMOJI} I lack permissions to perform this action.")
        else:
            await ctx.send(f"{FAIL_EMOJI} Error: {error}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
