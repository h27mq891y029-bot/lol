import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import asyncio
import io
import os
from dotenv import load_dotenv
from flask import Flask
from typing import List
import threading


app = Flask("")
@app.route("/")
def home():
    return "lol"

def run():
    app.run(host="0.0.0.0", port=8080)
threading.Thread(target=run).start()


load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
APYHUB_TOKEN = os.getenv("APYHUB_API")




intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

API_URL = "https://api.apyhub.com/generate/gif/file"


async def video2gif(file: discord.Attachment):

    try:
        video_bytes = await file.read()
        filename = file.filename

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field("video", video_bytes, filename=filename, content_type="video/mp4")

            headers = {
                "apy-token": APYHUB_TOKEN
            }

            async with session.post(API_URL, data=form, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    return "Conversion failed"
                
                gif_bytes = await resp.read()
                return gif_bytes

    except Exception as e:
        return f"Error processing video: {e}"


from typing import List

@bot.tree.command(name="videotogif", description="Convert video(s) to GIF")
@app_commands.describe(files="Upload one or more video files")
async def videotogif(interaction: discord.Interaction, files: List[discord.Attachment]):
    if not files:
        await interaction.response.send_message("Please attach at least one video file", ephemeral=True)
        return

    await interaction.response.send_message(f"Processing {len(files)} video(s)…", ephemeral=True)

    tasks = [video2gif(f) for f in files]
    results = await asyncio.gather(*tasks)

    for i, result in enumerate(results):
        if isinstance(result, bytes):
            await interaction.followup.send(
                file=discord.File(fp=io.BytesIO(result), filename=f"{files[i].filename.rsplit('.',1)[0]}.gif")
            )
        else:
            await interaction.followup.send(result, ephemeral=True)



@bot.event
async def on_ready():
    print(f"[+] Logged in as {bot.user}")
    await bot.tree.sync()
    print("[+] Slash commands synced.")

bot.run(DISCORD_TOKEN)
