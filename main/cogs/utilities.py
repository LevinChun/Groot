from utils._type import *

import asyncio
import datetime
import random
import discord
import json
import unicodedata
import io
import re

from discord.ext import commands
from typing import Union
from utils.useful import Embed
from cogs.image import get_bytes
from discord.utils import _URL_REGEX

class Utilities(commands.Cog, description="Handy dandy utils"):
    def __init__(self, bot):
        self.bot = bot
        self.index = 0
        self.snipe_cache = {}
        self.esnipe_cache = {}

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        message = after
        if message.author.bot:
            return
        
        try:
            cache = self.esnipe_cache[message.channel.id]
        except KeyError:
            cache = self.esnipe_cache[message.channel.id] = []
        
        data = {"author": before.author, "before_content": before.content, "after_content": message.content, "message_obj": message}
        cache.append(data)
        await asyncio.sleep(300)
        cache.remove(data)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        try:
            cache = self.snipe_cache[message.channel.id]
        except KeyError:
            cache = self.snipe_cache[message.channel.id] = []
        
        cache.append(message)

        await asyncio.sleep(300)
        cache.remove(message)

    @commands.command(name="snipe", brief="Retrieves a recent deleted message")
    async def snipe(self, ctx: customContext, index=1):
        """
        Acts like a message log, but for channel specific and command only.\n
        Only returns the most recent message.
        A bot's deleted message is ignored.
        """
        try:
            cache = self.snipe_cache[ctx.channel.id]
        except KeyError:
            raise commands.BadArgument("There's nothing to snipe here.")

        try:
            message = cache[index-1]
        except IndexError:
            raise commands.BadArgument("There's nothing to snipe here.")

        em = Embed(
            title=f"Last deleted message in #{ctx.channel.name}",
            description=message.content,
            timestamp=discord.utils.utcnow(),
            colour=discord.Color.random(),
            url=message.jump_url
        )
        em.set_author(
            name=message.author,
            icon_url=message.author.avatar.url
        )
        em.set_footer(text=f"Sniped by: {ctx.author} | Index {index}/{len(cache)}")
        await ctx.send(embed=em)

    @commands.command(name="editsnipe", brief="Retrieves a recently edited message", aliases=['esnipe'])
    async def editsnipe(self, ctx: customContext, index=1):
        """
        Same as `snipe`, but for edited messages.
        A bot's edited message is ignored.
        """
        try:
            cache = self.esnipe_cache[ctx.channel.id]
        except KeyError:
            raise commands.BadArgument("There's nothing to snipe here.")

        try:
            message = cache[index-1]
        except IndexError:
            raise commands.BadArgument("There's nothing to snipe here.")

        em = Embed(
            title=f"Last edited message in #{ctx.channel.name}",
            description="**Before:**\n"
            f"+ {message['before_content']}\n"
            f"\n**After:**\n- {message['after_content']}",
            timestamp=discord.utils.utcnow(),
            colour=discord.Color.random(),
            url=message['message_obj'].jump_url
        )
        em.set_author(
            name=message['author'],
            icon_url=message['author'].avatar.url
        )

        em.set_footer(text=f"Sniped by: {ctx.author} | Index {index}/{len(cache)}")
        await ctx.send(embed=em)

    @commands.command(name="choose")
    async def choose(self, ctx: customContext, *choices):
        """
        Choose between the supplied things seperated by spaces.
        """
        if len(choices) < 2:
            raise commands.BadArgument(f"Please supply at least two choices.")
        await ctx.send(random.choice(choices))

    @commands.command(
        name="ui", aliases=["whois"], brief="Displays an user's information"
    )
    async def ui(self, ctx: customContext, member: discord.Member = None):
        """
        Shows all the information about the specified user.\n
        If none is specified, it defaults to the author.
        """
        member = member if member else ctx.author
        guild = ctx.guild
        status = member.raw_status
        
        def format_dt(dt: datetime.datetime, style=None):
            if style is None:
                return f'<t:{int(dt.timestamp())}>'
            return f'<t:{int(dt.timestamp())}:{style}>'
        em = Embed(
            title="",
            description=f"{member.mention}",
            timestamp=discord.utils.utcnow(),
        )
        em.add_field(
            name="Joined at", value=f"{format_dt(member.joined_at)} ({format_dt(member.joined_at, 'R')})"
        )
        em.add_field(
            name="Created at", value=f"{format_dt(member.created_at)} ({format_dt(member.created_at, 'R')})"
        )
        roles = member.roles[1:30]

        if roles:
            em.add_field(
                name=f"Roles [{len(member.roles) -1}]",
                value=" ".join(f"{role.mention}" for role in roles),
                inline=False,
            )
        else:
            em.add_field(
                name=f"Roles [{len(member.roles) -1}]",
                value="This member has no roles",
                inline=False,
            )



        em.add_field(name=f"Status:", value=f"{self.bot.icons[status]} {status.capitalize()}")

        # Activity
        activity = member.activity or "No activity currently"
        if isinstance(activity, discord.BaseActivity):
            em.add_field(name="Activity:", value=activity.name, inline=False)
        else:
            em.add_field(name="Activity:", value="No activity currently", inline=False)
        em.set_thumbnail(url=member.avatar.url)
        em.set_author(name=f"{member}", icon_url=member.avatar.url)
        em.set_footer(text=f"User ID: {member.id}")
        await ctx.send(embed=em)

    @commands.command(name="avatar", aliases=["av"], brief="Displays a member's avatar")
    async def avatar(self, ctx: customContext, member: discord.Member = None):
        """
        Displays a 1024 pixel sized image of the given member's avatar.
        If no member is specified, it defaults to the author's avatar.
        """
        member = member if member else ctx.author
        if member:
            em = Embed(
                title=f"Avatar for {member}",
                description=f'Link as\n[png]({member.avatar.replace(format="png",size=1024).url}) | [jpg]({member.avatar.replace(format="jpg",size=1024).url}) | [webp]({member.avatar.replace(format="webp",size=1024).url})',
                colour=discord.Color.blurple(),
            )
            em.set_image(url=member.avatar.url)
            await ctx.send(embed=em)

    @commands.command(name="archive", aliases=['save', 'arch'])
    async def _archive(self, ctx, *, message: Optional[discord.Message]):
        """
        Archive a message to your DM's by either
        supplying a message ID or replying to one.
        """

        if not message:
            message = getattr(ctx.message.reference, "resolved", None)
        
        if not message:
            raise commands.BadArgument(f"{self.bot.icons['redTick']} | You must either reply to a message, or pass in a message ID/jump url")

        # Resort message
        content = message.content or "_No content_"
        em = Embed(title="You archived a message!", url=message.jump_url, description=content, timestamp=discord.utils.utcnow())
        em.set_author(name=message.author, icon_url=message.author.avatar.url)
        try:
            msg = await ctx.author.send(embed=em)
            await msg.pin()
            await ctx.send(f"Archived the message in your DMs!\n{msg.jump_url}")
        except discord.Forbidden:
            await ctx.send("Oops! I couldn't send you a message. Are you sure your DMs are on?")

    @commands.command(name="id", usage="<channel | emoji | user>")
    async def _get_id(self, ctx: customContext, arg: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel, discord.Emoji, discord.User]):
        """
        Gets the ID from either a channel, an emoji or a user
        The emoji can **not** be a default emoji (they don't have ID's)
        """
        if not isinstance(arg, discord.Emoji):
            await ctx.send(f"\\{arg.mention}", allowed_mentions=discord.AllowedMentions(users=False))
        else:
            await ctx.send(f"\\<:{arg.name}:{arg.id}>")
    
    @commands.command(name="embed")
    async def _send_embed(self, ctx: customContext, *, embed: str):
        """
        Takes an embed dictionary as args and sends the embed.
        For more information see the documentation on Discord's official website.
        """
        em = discord.Embed.from_dict(json.loads(embed))
        await ctx.send(embed=em)
    

    # AFK command related things.
    def is_afk(self, user_id) -> bool:
        return user_id in self.bot.cache['afk_users']
    
    def get_afk(self, user_id) -> dict:
        return self.bot.cache['afk_users'][user_id]

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if self.is_afk(message.author.id):
            del self.bot.cache['afk_users'][message.author.id]
            return await message.channel.send(f"Welcome back {message.author.name}! I've removed your **AFK** status.")
        
        mentions = [member.id for member in message.mentions]
        for mention in mentions:
            if self.is_afk(mention):
                user_data = self.get_afk(mention)
                return await message.channel.send(f"{self.bot.get_user(mention)} is **AFK** with message: {user_data[0]} (<t:{user_data[1]}:R>)")


    @commands.command(name='afk', aliases=['setafk'], usage='[reason]')
    async def _set_afk(self, ctx: customContext, *, reason: str = "No reason provided."):
        """
        Marks you as AFK with given reason.
        When you get pinged, the bot will respond with the reason.
        """
        if self.is_afk(ctx.author.id):
            del self.bot.cache['afk_users'][ctx.author.id]
        
        await ctx.reply(f"{self.bot.icons['greenTick']} **{ctx.author.name}** is now AFK: {reason}")

        await asyncio.sleep(3)
        self.bot.cache['afk_users'][ctx.author.id] = (reason, int(discord.utils.utcnow().timestamp()))

    @commands.command()
    async def charinfo(self, ctx: customContext, *, characters: str):
        """
        Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'
        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send('Output too long to display.')
        await ctx.send(msg)

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_emojis=True)
    async def emoji(self, ctx: customContext):
        """
        Useful command to add, remove or edit an emoji.
        You must have the `manage_emojis` permission to use this.
        """
        await ctx.send_help(ctx.command)
    
    @emoji.command(name='add', aliases=['create'])
    async def emoji_add(self, ctx: customContext, name:str, *, image: Optional[Union[discord.Emoji, discord.PartialEmoji, discord.Member, str]]):
        """
        Takes an image link and makes an emoji with that image.
        Emoji name must be unique and the name length must be in between 2 and 32.
        """
        try:
            byt = await get_bytes(ctx, image, self.bot.session)
            emoji = await ctx.guild.create_custom_emoji(name=name, image=byt, reason=f'Responsible user: {ctx.author}')
        except (KeyError, discord.HTTPException):
            await ctx.send_help(ctx.command)
            return
        
        await ctx.send(f'Created {emoji} with name `{emoji.name}`')

    @emoji.command(name='delete', aliases=['remove'])
    async def emoji_delete(self, ctx: customContext, *, emoji: discord.Emoji):
        """
        Deletes the given emoji from the server.
        """
        await emoji.delete(reason=f'Responsible user: {ctx.author}')
        await ctx.send(f'Deleted `{emoji.name}` from this server.')

    @emoji.command(name='rename')
    async def emoji_rename(self, ctx: customContext, emoji: discord.Emoji, *, name:str):
        """
        Renames the given emoji to the given name.
        """
        await emoji.edit(name=name)
        await ctx.send(f'Renamed {emoji} from `{emoji.name}` to `{name}`.')
    
    @commands.command(aliases=['ss'])
    @commands.is_nsfw()
    async def screenshot(self, ctx: customContext, *, url: str):
        """
        Takes a screenshot of the given website.
        """

        url = url.strip('<>')
        if not re.match(_URL_REGEX, url):
            raise commands.BadArgument('That is not a valid url. Try again with a valid one.')
        res = await self.bot.session.get(f'https://image.thum.io/get/{url}')
        byt = io.BytesIO(await res.read())

        em = Embed(description=f'`URL`: {url}')
        em.set_image(url=f'attachment://{ctx.command.name}.png')
        await ctx.send(embed=em, file=discord.File(byt, filename=f'{ctx.command.name}.png'))

def setup(bot):
    bot.add_cog(Utilities(bot), cat_name="Utilities")
