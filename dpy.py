import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import os
from flask import Flask
import threading

app = Flask("")
@app.route("/")
def home():
    return "Bot alive"

def run():
    app.run(host="0.0.0.0", port=8080)
threading.Thread(target=run).start()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    allowed_contexts=discord.app_commands.AppCommandContext(
        guild=True,
        dm_channel=True,
        private_channel=True
    ),
    allowed_installs=discord.app_commands.AppInstallationType(
        guild=True,
        user=True
    ),
)

EZGIF_UPLOAD_URL = "https://s3.ezgif.com/upload-video"

async def video2gif(file: discord.Attachment):
    video_bytes = await file.read()
    async with aiohttp.ClientSession() as session:
        form = aiohttp.FormData()
        form.add_field("new", video_bytes, filename=file.filename, content_type="video/mp4")
        async with session.post(EZGIF_UPLOAD_URL, data=form) as resp:
            if resp.status != 200:
                return f"Upload failed for {file.filename}"
            html = await resp.text()
            import re
            match = re.search(r'action="(/video-to-gif/[^"]+)"', html)
            if not match:
                return f"Failed to parse EZGIF response for {file.filename}"
            convert_url = f"https://ezgif.com{match.group(1)}"
            form2 = aiohttp.FormData()
            form2.add_field("file", "")
            async with session.post(convert_url, data=form2) as conv_resp:
                if conv_resp.status != 200:
                    return f"Conversion failed for {file.filename}"
                conv_html = await conv_resp.text()
                gif_match = re.search(r'<div class="thumbnail">\s*<img src="([^"]+)"', conv_html)
                if not gif_match:
                    return f"Failed to get GIF URL for {file.filename}"
                return f"https:{gif_match.group(1)}"

@app_commands.command(name="videotogif", description="Convert multiple videos to GIFs via EZGIF")
@app_commands.describe(
    file1="Video file 1",
    file2="Video file 2 (optional)",
    file3="Video file 3 (optional)"
)
async def videotogif(interaction: discord.Interaction, file1: discord.Attachment, file2: discord.Attachment=None, file3: discord.Attachment=None):
    files = [f for f in (file1, file2, file3) if f]
    await interaction.response.send_message(f"Processing {len(files)} video(s)...", ephemeral=True)
    results = await asyncio.gather(*[video2gif(f) for f in files])
    for f, res in zip(files, results):
        if res.startswith("http"):
            await interaction.followup.send(f"{f.filename}: {res}")
        else:
            await interaction.followup.send(res, ephemeral=True)

bot.tree.add_command(videotogif)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

bot.run(DISCORD_TOKEN)
