# -*- coding: utf-8 -*-

"""
pycord.cog
~~~~~~~~~~~~

The pycord debugging and diagnostics cog implementation.

Does **not** include ext's or non-features

:copyright: (c) 2021 Devon (Gorialis) R
:license: MIT, see LICENSE for more details.

"""

from discord.ext import commands

from pycord.features.filesystem import FilesystemFeature
from pycord.features.guild import GuildFeature
from pycord.features.invocation import InvocationFeature
from pycord.features.management import ManagementFeature
from pycord.features.python import PythonFeature
from pycord.features.root_command import RootCommand
from pycord.features.shell import ShellFeature
from pycord.features.voice import VoiceFeature

__all__ = (
    "pycord",
    "STANDARD_FEATURES",
    "OPTIONAL_FEATURES",
    "setup",
)

STANDARD_FEATURES = (
    VoiceFeature,
    GuildFeature,
    FilesystemFeature,
    InvocationFeature,
    ShellFeature,
    PythonFeature,
    ManagementFeature,
    RootCommand,
)

OPTIONAL_FEATURES = []

try:
    from pycord.features.youtube import YouTubeFeature
except ImportError:
    pass
else:
    OPTIONAL_FEATURES.insert(0, YouTubeFeature)


class pycord(
    *OPTIONAL_FEATURES, *STANDARD_FEATURES
):  # pylint: disable=too-few-public-methods
    """
    The frontend subclass that mixes in to form the final pycord cog.
    """


def setup(bot: commands.Bot):
    """
    The setup function defining the pycord.cog and pycord extensions.
    """

    bot.add_cog(pycord(bot=bot))
