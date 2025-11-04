import os
import threading
import aiohttp
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from dotenv import load_dotenv

flask_app = Flask(__name__)
@flask_app.route("/")
def home():
    return "Bot is alive!"
threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080), daemon=True).start()

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TENOR_API_KEY = os.getenv("TENOR_API_KEY")
if not DISCORD_TOKEN or not TENOR_API_KEY:
    raise RuntimeError("Missing DISCORD_TOKEN or TENOR_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

TENOR_UPLOAD_URL = "https://api.tenor.com/v2/upload"

async def upload_to_tenor(video_url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url, timeout=30) as resp:
                if resp.status != 200:
                    return f"Download failed ({resp.status})"
                video_bytes = await resp.read()
                if len(video_bytes) > 100 * 1024 * 1024:
                    return "Video too large (>100MB)"
    except Exception as e:
        return f"Download error: {str(e)}"

    form_data = aiohttp.FormData()
    form_data.add_field("file", video_bytes, filename="video.mp4", content_type="video/mp4")
    form_data.add_field("key", TENOR_API_KEY)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(TENOR_UPLOAD_URL, data=form_data, timeout=120) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    return f"Upload failed ({resp.status}): {text[:100]}"
                result = await resp.json()
                gif_id = result.get("media", [{}])[0].get("id")
                if not gif_id:
                    return "No GIF created."
                return f"https://tenor.com/view/{gif_id}"
    except Exception as e:
        return f"Upload error: {str(e)}"

@app_commands.command(name="urltogif", description="Convert up to 3 video URLs to Tenor GIFs")
@app_commands.describe(
    url1="Video URL 1 (mp4, mov, webm)",
    url2="Video URL 2 (optional)",
    url3="Video URL 3 (optional)"
)
async def urltogif(
    interaction: discord.Interaction,
    url1: str,
    url2: str | None = None,
    url3: str | None = None
):
    urls = [u.strip() for u in (url1, url2, url3) if u and u.strip()]
    if not urls:
        await interaction.response.send_message("Provide at least one URL.", ephemeral=True)
        return
    await interaction.response.send_message(f"Uploading {len(urls)} video(s)...", ephemeral=True)
    results = await asyncio.gather(*[upload_to_tenor(u) for u in urls])
    for result in results:
        await interaction.followup.send(result)

bot.tree.add_command(urltogif)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()
    print("/urltogif ready")

bot.run(DISCORD_TOKEN)
