import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import io
import os
from dotenv import load_dotenv
from flask import Flask
import threading

app = Flask("")
@app.route("/")
def home():
    return "Bot alive"

def run():
    app.run(host="0.0.0.0", port=8080)
threading.Thread(target=run).start()

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
APYHUB_TOKEN = os.getenv("APYHUB_API")

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

API_URL = "https://api.apyhub.com/generate/gif/file"

async def video2gif(file: discord.Attachment):
    video_bytes = await file.read()
    async with aiohttp.ClientSession() as session:
        form = aiohttp.FormData()
        form.add_field("video", video_bytes, filename=file.filename, content_type="video/mp4")
        headers = {"apy-token": APYHUB_TOKEN}
        async with session.post(API_URL, data=form, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                return f"Conversion failed for {file.filename}: {text}"
            return await resp.read()

@app_commands.command(name="videotogif", description="Convert video(s) to GIF")
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
        if isinstance(res, bytes):
            await interaction.followup.send(file=discord.File(fp=io.BytesIO(res), filename=f"{f.filename.rsplit('.',1)[0]}.gif"))
        else:
            await interaction.followup.send(res, ephemeral=True)

bot.tree.add_command(videotogif)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Commands synced")

bot.run(DISCORD_TOKEN)
