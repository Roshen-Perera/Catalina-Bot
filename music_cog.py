import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import logging
import asyncio

class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_playing = {}         # {guild_id: bool}
        self.is_paused = {}          # {guild_id: bool}
        self.music_queue = {}        # {guild_id: [[song, voice_channel], ...]}
        self.vc = {}                 # {guild_id: discord.VoiceClient}

        self.YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'extract_flat': False
        }
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

    # -------------------- Helper Methods --------------------

    def search_yt(self, item):
        """Search YouTube and return streamable URL + title."""
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                if item.startswith("http://") or item.startswith("https://"):
                    info = ydl.extract_info(item, download=False)
                else:
                    info = ydl.extract_info(f"ytsearch:{item}", download=False)
                    if 'entries' in info:
                        info = info['entries'][0]

                url = info.get('url')
                if not url:
                    logging.error("No valid URL found in video info")
                    return None

                return {'source': url, 'title': info.get('title', 'Unknown')}
            except Exception as e:
                logging.error(f"Error searching YouTube: {e}")
                return None

    async def play_music(self, guild_id):
        """Play the next song in queue for this guild."""
        if guild_id not in self.music_queue or not self.music_queue[guild_id]:
            self.is_playing[guild_id] = False
            return

        song, voice_channel = self.music_queue[guild_id][0]
        m_url = song['source']

        # Connect or move to voice channel
        if guild_id not in self.vc or not self.vc[guild_id] or not self.vc[guild_id].is_connected():
            self.vc[guild_id] = await voice_channel.connect()
        else:
            await self.vc[guild_id].move_to(voice_channel)

        self.is_playing[guild_id] = True
        self.is_paused[guild_id] = False

        # Send "Now playing" message
        if voice_channel.guild.text_channels:
            await voice_channel.guild.text_channels[0].send(f"🎶 Now playing: **{song['title']}**")

        # Callback after song finishes
        def after_playing(error):
            if error:
                logging.error(f"Playback error: {error}")
            self.music_queue[guild_id].pop(0)
            if self.music_queue[guild_id]:
                fut = asyncio.run_coroutine_threadsafe(self.play_music(guild_id), self.bot.loop)
                try:
                    fut.result()
                except Exception as e:
                    logging.error(f"Error in after callback: {e}")
            else:
                self.is_playing[guild_id] = False

        self.vc[guild_id].play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=after_playing)

    # -------------------- Music Commands --------------------

    @commands.hybrid_command(name="mplay", aliases=["mp"], help="Play a song from YouTube (search query or URL)")
    async def mplay(self, ctx, *, query: str):
        guild_id = ctx.guild.id

        if guild_id not in self.music_queue:
            self.music_queue[guild_id] = []
            self.is_playing[guild_id] = False
            self.is_paused[guild_id] = False

        if not ctx.author.voice:
            await ctx.send("❌ You need to be connected to a voice channel!")
            return
        voice_channel = ctx.author.voice.channel

        await ctx.send("🔎 Searching...")
        song = self.search_yt(query)
        if not song:
            await ctx.send("❌ Could not retrieve the song. Try another keyword or URL.")
            return

        # Stop radio if playing
        if self.vc.get(guild_id) and self.is_playing.get(guild_id):
            self.vc[guild_id].stop()
            await asyncio.sleep(0.1)
            self.is_playing[guild_id] = False

        # Clear queue and play immediately
        self.music_queue[guild_id] = [[song, voice_channel]]
        await ctx.send(f"✅ Playing now: **{song['title']}**")
        await self.play_music(guild_id)

    @commands.hybrid_command(name="mpause", help="Pauses the current song")
    async def mpause(self, ctx):
        guild_id = ctx.guild.id
        if self.vc.get(guild_id) and self.vc[guild_id].is_playing():
            self.vc[guild_id].pause()
            self.is_paused[guild_id] = True
            await ctx.send("⏸️ Paused the music.")
        else:
            await ctx.send("❌ No music is currently playing.")

    @commands.hybrid_command(name="mresume", aliases=["mr"], help="Resumes the song")
    async def mresume(self, ctx):
        guild_id = ctx.guild.id
        if self.vc.get(guild_id) and self.vc[guild_id].is_paused():
            self.vc[guild_id].resume()
            self.is_paused[guild_id] = False
            await ctx.send("▶️ Resumed the music.")
        else:
            await ctx.send("❌ Music is not paused.")

    @commands.hybrid_command(name="mskip", aliases=["ms"], help="Skips the current song")
    async def mskip(self, ctx):
        guild_id = ctx.guild.id
        if self.vc.get(guild_id) and self.is_playing.get(guild_id):
            self.vc[guild_id].stop()
            await ctx.send("⏭️ Skipped the song.")
        else:
            await ctx.send("❌ No music is currently playing.")

    @commands.hybrid_command(name="mqueue", aliases=["mq"], help="Show the current queue")
    async def mqueue(self, ctx):
        guild_id = ctx.guild.id
        queue = self.music_queue.get(guild_id)
        if not queue:
            await ctx.send("📭 Queue is empty.")
            return

        msg = "**🎶 Current Queue:**\n"
        for i, song in enumerate(queue[:10]):
            msg += f"{i+1}. {song[0]['title']}\n"
        if len(queue) > 10:
            msg += f"\n... and {len(queue)-10} more"
        await ctx.send(msg)

    @commands.hybrid_command(name="mclear", aliases=["mc"], help="Clear the queue")
    async def mclear(self, ctx):
        guild_id = ctx.guild.id
        if self.vc.get(guild_id) and self.is_playing.get(guild_id):
            self.vc[guild_id].stop()
        self.music_queue[guild_id] = []
        await ctx.send("🗑️ Queue cleared.")

    @commands.hybrid_command(name="mleave", aliases=["ml"], help="Leave the voice channel")
    async def mleave(self, ctx):
        guild_id = ctx.guild.id
        self.is_playing[guild_id] = False
        self.is_paused[guild_id] = False
        if self.vc.get(guild_id):
            await self.vc[guild_id].disconnect()
            self.vc[guild_id] = None
            await ctx.send("👋 Disconnected from the voice channel.")
        else:
            await ctx.send("❌ Not connected to any voice channel.")

    # -------------------- Radio Commands --------------------

    @commands.hybrid_command(name="radio", help="Play a radio stream by URL or predefined station")
    async def radio(self, ctx, *, url: str = None):
        guild_id = ctx.guild.id
        if not ctx.author.voice:
            await ctx.send("❌ You need to be in a voice channel!")
            return
        voice_channel = ctx.author.voice.channel

        if not self.vc.get(guild_id) or not self.vc[guild_id].is_connected():
            self.vc[guild_id] = await voice_channel.connect()
        else:
            await self.vc[guild_id].move_to(voice_channel)

        radio_url = url or "https://stream.example.com/default_radio.mp3"

        # Stop any music queue or old radio
        if self.music_queue.get(guild_id):
            self.music_queue[guild_id] = []

        if self.vc.get(guild_id) and (self.vc[guild_id].is_playing() or self.vc[guild_id].is_paused()):
            self.vc[guild_id].stop()
            await asyncio.sleep(0.1)

        self.is_playing[guild_id] = True
        self.is_paused[guild_id] = False

        def after_radio(error):
            if error:
                logging.error(f"Radio playback error: {error}")
            self.is_playing[guild_id] = False

        self.vc[guild_id].play(discord.FFmpegPCMAudio(radio_url, **self.FFMPEG_OPTIONS), after=after_radio)
        await ctx.send(f"📻 Now playing radio: **{radio_url}**")

    @commands.hybrid_command(name="rstop", help="Stop the radio stream")
    async def rstop(self, ctx):
        guild_id = ctx.guild.id
        if self.vc.get(guild_id) and self.is_playing.get(guild_id):
            self.vc[guild_id].stop()
            self.is_playing[guild_id] = False
            await ctx.send("⏹️ Stopped the radio stream.")
        else:
            await ctx.send("❌ No radio is currently playing.")

    @commands.hybrid_command(name="rinfo", help="Get info about the current radio stream")
    async def rinfo(self, ctx):
        guild_id = ctx.guild.id
        if self.is_playing.get(guild_id):
            await ctx.send("📻 Radio is currently playing.")
        else:
            await ctx.send("❌ No radio is playing right now.")
