import os
import threading
import aiohttp
import asyncio
import json
import subprocess
import tempfile
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from dotenv import load_dotenv

# Keep-alive for Render
flask_app = Flask(__name__)
@flask_app.route("/")
def home():
    return "Bot alive"
threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080), daemon=True).start()

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def instagram_to_gif(insta_url: str, channel: discord.TextChannel) -> str:
    try:
        # 1. Scrape Instagram
        scrape_url = f"{insta_url}?__a=1&__d=dis"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.get(scrape_url, timeout=30) as r:
                if r.status != 200:
                    return f"Scrape failed ({r.status}) – public post only"
                txt = await r.text()
                data = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
                media = data["graphql"]["shortcode_media"]
                if not media.get("is_video"):
                    return "No video in this post"
                video_url = media["video_url"]

        # 2. Download video
        async with aiohttp.ClientSession() as s:
            async with s.get(video_url, timeout=60) as r:
                if r.status != 200:
                    return f"Download failed ({r.status})"
                video_bytes = await r.read()
                if len(video_bytes) > 100 * 1024 * 1024:
                    return "Video >100 MB"

        # 3. Temp files
        mp4_path = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
        gif_path = tempfile.NamedTemporaryFile(suffix=".gif", delete=False).name
        open(mp4_path, "wb").write(video_bytes)

        # 4. FFmpeg → GIF
        subprocess.run([
            "ffmpeg", "-y", "-i", mp4_path,
            "-vf", "fps=10,scale=300:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            "-loop", "0", gif_path
        ], check=True, capture_output=True, timeout=60)

        # 5. Upload GIF
        with open(gif_path, "rb") as f:
            msg = await channel.send(file=discord.File(f, "instagram.gif"))
            return f"**GIF Ready!**\n{msg.attachments[0].url}"

    except json.JSONDecodeError:
        return "Invalid response – private post or blocked"
    except Exception as e:
        return f"Error: {e}"
    finally:
        for p in (mp4_path, gif_path):
            if os.path.exists(p):
                os.unlink(p)

@app_commands.command(name="instagif", description="Instagram → GIF (uploads to Discord)")
@app_commands.describe(insta_url="Public Instagram post/Reel URL")
async def instagif(interaction: discord.Interaction, insta_url: str):
    if "instagram.com" not in insta_url:
        return await interaction.response.send_message("Give a valid Instagram URL", ephemeral=True)
    await interaction.response.send_message("Downloading & converting...", ephemeral=True)
    result = await instagram_to_gif(insta_url, interaction.channel)
    await interaction.followup.send(result)

bot.tree.add_command(instagif)

@bot.event
async def on_ready():
    print(f"Logged in: {bot.user}")
    await bot.tree.sync()
    print("/instagif ready")

bot.run(DISCORD_TOKEN)
