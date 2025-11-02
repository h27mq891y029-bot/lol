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
from bs4 import BeautifulSoup

app = Flask("")
@app.route("/")
def home():
    return "Bot alive"

def run():
    app.run(host="0.0.0.0", port=8080)
threading.Thread(target=run).start()

load_dotenv()
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
    filename = file.filename
    headers = {"User-Agent": "Mozilla/5.0"}
    data = aiohttp.FormData()
    data.add_field("new", video_bytes, filename=filename, content_type="video/mp4")

    async with aiohttp.ClientSession() as session:
        async with session.post(EZGIF_UPLOAD_URL, data=data, headers=headers) as resp:
            if resp.status != 200:
                return f"Upload failed for {filename}: {resp.status}"
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            gif_form = soup.find("form", {"id": "tool-submit-form"})
            if not gif_form:
                return f"Failed to parse EZGIF response for {filename}"
            gif_url_input = gif_form.find("input", {"name": "file"})
            if not gif_url_input:
                return f"Failed to get GIF URL for {filename}"
            gif_file = gif_url_input["value"]
            return f"https://ezgif.com/{gif_file}"

@app_commands.command(name="videotogif", description="Convert video(s) to GIF")
@app_commands.describe(
    file1="Video file 1",
    file2="Video file 2 (optional)",
    file3="Video file 3 (optional)"
)
async def videotogif(interaction: discord.Interaction, file1: discord.Attachment, file2: discord.Attachment=None, file3: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    files = [f for f in (file1, file2, file3) if f]
    tasks = [video2gif(f) for f in files]
    results = await asyncio.gather(*tasks)
    for f, res in zip(files, results):
        await interaction.followup.send(f"{f.filename}: {res}")

bot.tree.add_command(videotogif)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("Commands synced")

bot.run(DISCORD_TOKEN)
