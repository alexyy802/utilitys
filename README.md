![Logo](pyc_utils.png)

# Utilitys

Utility Plugin For [Pycord](https://github.com/pycord-development/pycord)

# Features:

- Advanced Audio Plug-ins
- Custom Cog For Easier Bot Use
- IPC & Alternatives
- Specialized For Use With Pycord

# Installing:

### Stable:

```py
pip install --upgrade pycord-utils
```

### Development:

```py
pip install -U git+https://github.com/pycord/utilitys.git
```

# Extra Option's

### Using our Custom Cog

First Install the extra version of Pycord Utilitys

```py
pip install -U pycord-utils[extra]
```

Then Add This To Your Main bot file

```py
bot.load_extension('pycord')
```

And your done!

### Voice

To use our Voice Options Install 

```py
pip install -U pycord-utils[voice]

```

### Example
```py
import pycord
from discord.ext import audio
from pycord.ext import commands

bot = commands.Bot(command_prefix="!")

@bot.event
async def on_ready():
    print('Bot is online.')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! :ping_pong:')

bot.run("TOKEN")
```
More examples can be found in the examples folder.


### Creators
- VincentRPS [Main Files, IPC Maker, etc]
- AlexyDaCoder [README.md edit master, Alternative Creator]
