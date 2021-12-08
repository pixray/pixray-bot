import os
import requests
import json
import urllib
import time
from tqdm import tqdm
from dotenv import load_dotenv
from discord.ext import commands
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PIXRAY_API = "https://replicate.com/api/models/dribnet/pixray-api/versions/a249606da3a0c7f32eed4741f1e6f1792470a39a5825fc8814272cceea30ad32/predictions"
PIXRAY_JSON = '{ "inputs": { "settings" :  { "prompts" : "%PROMPT%" } } }'
HEADERS = {'Content-type': 'application/json'}
POLL_API = "https://replicate.com/api/models/dribnet/pixray-api/versions/a249606da3a0c7f32eed4741f1e6f1792470a39a5825fc8814272cceea30ad32/predictions"
OUTPUT_PREFIX = "https://replicate.com/api/models/dribnet/pixray-api/files"
OUTFILE = "outfile.png"

bot = commands.Bot(command_prefix='pixray/')

@bot.event
async def on_ready():
    print('We have successfully loggged in as {0.user}'.format(bot))

class Commands(commands.Cog, name='Commands'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='create', brief='Generate a pixray image.')
    @commands.has_role('attendee')
    async def create(self, context, query: str):
        if context.author == self.bot.user:
            return

        if query.lower() == 'hello':
            await context.send(f'Hello, {context.author.display_name}!')
            return

        if query.lower() == 'bye':
            await context.send(f'See you later, {context.author.display_name}!')
            return

        json = PIXRAY_JSON.replace('%PROMPT%', query.lower())
        print(f'Getting started ({json})')
        r = requests.post(PIXRAY_API, data=json, headers=HEADERS)
        print(r.status_code)
        response = r.json()

        uuid = response['uuid']
        status = response['status']
        error = response['error']
        print(f'New session started ({uuid}) with status {status} and error {error}')

        poll_url = f'{POLL_API}/{uuid}'

        while (status == 'queued' or status == 'processing') and (error == None):
            time.sleep(5)
            r = requests.get(poll_url)
            response = r.json()
            status = response['prediction']['status']
            error = response['prediction']['error']
            print(f'Sessions update: status {status} and error {error}')

        if status != 'success':
            print('Sorry, something bad happened :-(')
            print(f'FINAL RESPONSE: {response}')
            return

        out_url = f"{OUTPUT_PREFIX}/{response['prediction']['output_file']}"
        print(f'DONE! Downloading: {out_url}')
        response = requests.get(out_url, stream=True)

        with open(OUTFILE, 'wb') as handle:
            for data in tqdm(response.iter_content()):
                handle.write(data)

        print(f'Download complete, data saved in {OUTFILE}')

        await context.send(file=discord.File(OUTFILE))
        return

bot.add_cog(Commands(bot))
bot.run(TOKEN)
