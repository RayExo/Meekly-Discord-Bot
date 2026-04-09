import discord
from discord.ext import commands
from discord.ui import LayoutView, Container, Section, TextDisplay, Separator, Thumbnail

class Botlink(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='invite', aliases=['inv'], help="Get the bot's invite link.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def invite(self, ctx):
        section = Section(
            TextDisplay(
                f"# **Bot Invite Link**\n"
                f"> Invite {self.bot.user.name} to your server using the link below:\n\n"
                f"> [**Click Here to Invite**]({self.bot.invite_link})"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Bot Invite Thumbnail"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Developed by Meekly Development™")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name='support', aliases=['supp', 'server'], help="Get the bot's support server link.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def support(self, ctx):
        section = Section(
            TextDisplay(
                f"# **Support Server**\n"
                f"> Join the official support server for {self.bot.user.name}:\n\n"
                f"> [**Join Support Server**]({self.bot.support_link})"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Support Server Thumbnail"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Developed by Meekly Development™")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

    @commands.command(name='vote', aliases=['v'], help="Get the bot's top.gg vote link.")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def vote(self, ctx):
        section = Section(
            TextDisplay(
                f"# **Vote for {self.bot.user.name}**\n"
                f"> Show your support by voting on top.gg:\n\n"
                f"> [**Click Here to Vote**]({self.bot.vote_link})"
            ),
            accessory=Thumbnail(
                media=discord.UnfurledMediaItem(url=self.bot.user.display_avatar.url),
                description="Vote Thumbnail"
            ),
            id=1
        )
        container = Container(
            section,
            Separator(),
            TextDisplay("-# Developed by Meekly Development™")
        )
        view = LayoutView(timeout=None)
        view.add_item(container)
        await ctx.send(view=view)

async def setup(bot):
    await bot.add_cog(Botlink(bot))