from discord.ext.commands import BadArgument, converter, Context
from discord import Guild, utils

from ._common import _ALL

# Basic Guild Converter


class _GuildConverter(converter.IDConverter):
    async def convert(self, ctx: Context, argument: str):
        bot = ctx.bot

        match = self._get_id_match(argument)
        result = None

        if match is None:
            result = utils.get(bot.guilds, name=argument)
        else:
            guild_id = int(match.group(1))
            result = ctx.bot.get_guild(guild_id)

        if result is None:
            raise BadArgument('Guild "{}" not found'.format(argument))
        return result


converter.GuildConverter = _GuildConverter
_ALL[Guild] = _GuildConverter