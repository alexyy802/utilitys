pycord.ext.audio - Music Playing Extension
==========================================
Welcome to pycord.ext.audio Documentation Audio is a Music Extension For Pycord.


Getting Started
----------------------------

A quick and easy bot example:

.. code:: py

    import discord
    import pycord 
    from pycord.ext import audio
    from discord.ext import commands


    class Bot(commands.Bot):

        def __init__(self):
            super(Bot, self).__init__(command_prefix=['audio ', 'wave ','aw '])

            self.add_cog(Music(self))

        async def on_ready(self):
            print(f'Logged in as {self.user.name} | {self.user.id}')


    class Music(commands.Cog):

        def __init__(self, bot):
            self.bot = bot

            if not hasattr(bot, 'audio'):
                self.bot.audio = audio.Client(bot=self.bot)

            self.bot.loop.create_task(self.start_nodes())

        async def start_nodes(self):
            await self.bot.wait_until_ready()

            # Initiate our nodes. For this example we will use one server.
            # Region should be a discord.py guild.region e.g sydney or us_central (Though this is not technically required)
            await self.bot.audio.initiate_node(host='0.0.0.0',
                                                  port=2333,
                                                  rest_uri='http://0.0.0.0:2333',
                                                  password='youshallnotpass',
                                                  identifier='TEST',
                                                  region='us_central')

        @commands.command(name='connect')
        async def connect_(self, ctx, *, channel: discord.VoiceChannel=None):
            if not channel:
                try:
                    channel = ctx.author.voice.channel
                except AttributeError:
                    raise discord.DiscordException('No channel to join. Please either specify a valid channel or join one.')

            player = self.bot.audio.get_player(ctx.guild.id)
            await ctx.send(f'Connecting to **`{channel.name}`**')
            await player.connect(channel.id)

        @commands.command()
        async def play(self, ctx, *, query: str):
            tracks = await self.bot.audio.get_tracks(f'ytsearch:{query}')

            if not tracks:
                return await ctx.send('Could not find any songs with that query.')

            player = self.bot.audio.get_player(ctx.guild.id)
            if not player.is_connected:
                await ctx.invoke(self.connect_)

            await ctx.send(f'Added {str(tracks[0])} to the queue.')
            await player.play(tracks[0])


    bot = Bot()
    bot.run('TOKEN')

Client
----------------------------

.. autoclass:: pycord.ext.audio.client.Client
    :members:


Node
----------------------------

.. autoclass:: pycord.ext.audio.node.Node
    :members:


Player
----------------------------
.. autoclass:: pycord.ext.audio.player.Player
    :members:


Track
----------------------------
.. autoclass:: pycord.ext.audio.player.Track
    :members:

.. autoclass:: pycord.ext.audio.player.TrackPlaylist
    :members:


Equalizer
----------------------------
.. autoclass:: pycord.ext.audio.eqs.Equalizer
    :members:


Event Payloads
----------------------------

.. autoclass:: pycord.ext.audio.events.TrackStart
    :members:

.. autoclass:: pycord.ext.audio.events.TrackEnd
    :members:

.. autoclass:: pycord.ext.audio.events.TrackException
    :members:

.. autoclass:: pycord.ext.audio.events.TrackStuck
    :members:


audioMixin
-----------------------

.. warning::
    Listeners must be used with a `audio.audioMixin.listener()` decorator to work.

.. warning::
    Listeners must be coroutines.

.. autoclass:: pycord.ext.audio.meta.audioMixin
    :members:


Errors
-----------------------

.. autoexception:: pycord.ext.audio.errors.audioException

.. autoexception:: pycord.ext.audio.errors.NodeOccupied

.. autoexception:: pycord.ext.audio.errors.InvalidIDProvided

.. autoexception:: pycord.ext.audio.errors.ZeroConnectedNodes

.. autoexception:: pycord.ext.audio.errors.AuthorizationFailure
