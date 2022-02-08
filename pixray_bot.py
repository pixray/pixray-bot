import os
import requests
import json
import urllib
import asyncio
import aiohttp
from tqdm import tqdm
from dotenv import load_dotenv
from discord.ext import commands
import discord

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PIXRAY_API = "https://replicate.com/api/v1/models/pixray/api/versions/3a91754e77ee37f27531490d97f045085fc0ba84727dc2bf77cd18c2d110e324/predictions"
PIXRAY_JSON = '{ "inputs": { "settings" :  { "prompts" : "%PROMPT%", "drawer": "vdiff", "vdiff_model": "cc12m_1_cfg", "quality": "better", "scale": 2.25, "custom_loss": "aesthetic:0.5" } } }'
HEADERS = {'Content-type': 'application/json', 'Authorization': 'Token %TOKEN%'}
HEADERS_POLL = {'Authorization': 'Token %TOKEN%'}
POLL_API = PIXRAY_API
OUTPUT_PREFIX = "https://replicate.com/api/models/pixray/api/files"
OUTFILE = "outfile.png"

## apply TOKEN based on enviromnet
REPLICATE_TOKEN = os.environ.get('REPLICATE_TOKEN')
if REPLICATE_TOKEN is None:
    print("Please set REPLICATE_TOKEN in environment before running")
    sys.exit(1)
HEADERS['Authorization'] = HEADERS['Authorization'].replace("%TOKEN%", REPLICATE_TOKEN)
HEADERS_POLL['Authorization'] = HEADERS_POLL['Authorization'].replace("%TOKEN%", REPLICATE_TOKEN)

bot = commands.Bot(command_prefix='pixray/')

@bot.event
async def on_ready():
    print('We have successfully loggged in as {0.user}'.format(bot))

status_working = ['preparing', 'queued', 'processing']

class Commands(commands.Cog, name='Commands'):
    def __init__(self, bot):
        self.bot = bot
        self.uuids = {}

    def create_embed(self, title, query, uuid, status, error, image_url=None):
        embed = discord.Embed(
            title=title,
            description="powered by replicate.com",
            color=0x4168B5
        )
        embed.add_field(name="Query", value=query, inline=False)
        embed.add_field(name="UUID", value=uuid, inline=False)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Error", value=error, inline=True)
        if image_url is not None:
            embed.set_image(url=image_url)
        return embed

    @commands.command(name='create')
    # @commands.has_role('attendee')
    async def create(self, context: commands.Context, *, query: str.lower):
        """Queries pixray to generate an image from the given text.

        Parameters
        ----------
        query : str
            Query to generate image from (automatically lowercased)
        """
        if context.author == self.bot.user:
            return

        # Start a new session with user query
        # TODO: move to aiohttp for async requests
        json = PIXRAY_JSON.replace('%PROMPT%', query)
        print(f'Getting started ({json})')
        r = requests.post(PIXRAY_API, data=json, headers=HEADERS)
        print(r.status_code)
        response = r.json()
        uuid = response['uuid']
        status = response['status']
        error = response['error']
        print(f'New session started ({uuid}) with status {status} and error {error}')

        # Retain memory of query since multiple queries can be simultaneously sent
        self.uuids[uuid] = {
            'query': query,
            'status': status,
            'error': error,
            'author': context.author
        }

        poll_url = f'{POLL_API}/{uuid}'

        t = 0
        while status in status_working and error == None:
            if t == 0:
                embed = self.create_embed("Generating 🌱", query, uuid, status, error)
                await context.send(embed=embed)
            await asyncio.sleep(5)
            r = requests.get(poll_url, headers=HEADERS_POLL)
            response = r.json()
            status = response['prediction']['status']
            error = response['prediction']['error']
            self.uuids[uuid]['status'] = status
            self.uuids[uuid]['error'] = error
            print(f'Sessions update: status {status} and error {error}')
            t += 1

        if status != 'success':
            print('Sorry, something bad happened :-(')
            await context.send(f'Sorry, something bad happened :-( ({uuid})', delete_after=5)
            print(f'FINAL RESPONSE: {response}')
            return

        out_url = f"{OUTPUT_PREFIX}/{response['prediction']['output_file']}"
        print(f'DONE! Downloading: {out_url}')
        response = requests.get(out_url, stream=True, headers=HEADERS_POLL)

        # Delete uuid from dictionary after successful generation
        deleted_uuid = self.uuids.pop(uuid, None)

        with open(OUTFILE, 'wb') as handle:
            for data in tqdm(response.iter_content()):
                handle.write(data)

        print(f'Download complete, data saved in {OUTFILE}')
        file = discord.File(OUTFILE, filename=OUTFILE)
        embed = self.create_embed("Generation complete 🪴", query, uuid, status, error, f"attachment://{OUTFILE}")
        author = deleted_uuid['author']
        await context.send(f'{author.mention}', file=file, embed=embed)
        return

    @create.error
    async def create_error(self, context: commands.Context, error: commands.CommandError):
        """Handle errors for the create command."""
        if isinstance(error, commands.errors.CheckFailure):
            await context.send('You do not have the correct role for this command.', delete_after=5)
        # TODO: this isn't messaging the user for some reason. Fix it.
        if isinstance(error, discord.Forbidden):
            await context.author.send(f'This bot does not have the necessary permissions to post in {context.channel}.', delete_after=5)
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await context.send('Missing required argument.', delete_after=5)

    @commands.command(name='status')
    # @commands.has_role('attendee')
    async def status(self, context: commands.Context, uuid: str):
        """Query the status of a pixray query given a uuid.

        Parameters
        ----------
        uuid : str
            uuid of a pixray query
        """
        if context.author == self.bot.user:
            return

        if self.uuids is None or uuid not in self.uuids:
            await context.send(f'{uuid} does not exist.', delete_after=5)
            return

        author = self.uuids[uuid]['author'].nick
        query = self.uuids[uuid]['query']
        status = self.uuids[uuid]['status']
        error = self.uuids[uuid]['error']
        embed = discord.Embed(
            color=0x4168B5
        )
        embed.add_field(name="Query", value=query, inline=False)
        embed.add_field(name="UUID", value=uuid, inline=True)
        embed.add_field(name="Author", value=author, inline=True)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Error", value=error, inline=True)
        await context.send(embed=embed)
        return

    @status.error
    async def status_error(self, context: commands.Context, error: commands.CommandError):
        """Handle errors for the status command."""
        if isinstance(error, commands.errors.CheckFailure):
            await context.send('You do not have the correct role for this command.', delete_after=5)
        # TODO: this isn't messaging the user for some reason. Fix it.
        if isinstance(error, discord.Forbidden):
            await context.author.send(f'This bot does not have the necessary permissions to post in {context.channel}.', delete_after=5)
        if isinstance(error, commands.errors.MissingRequiredArgument):
            await context.send('Missing required argument.', delete_after=5)

    @commands.command(name='queue')
    # @commands.has_role('attendee')
    async def queue(self, context: commands.Context):
        """Display queue of queries being processed or queued by pixray."""
        if context.author == self.bot.user:
            return

        print(self.uuids)
        if not self.uuids:
            await context.send('Queue is empty.', delete_after=5)
            return

        embed = discord.Embed(
            title='Queries',
            color=0x4168B5
        )
        for uuid, info in self.uuids.items():
            embed.add_field(name="Query", value=info['query'], inline=True)
            embed.add_field(name="UUID", value=uuid, inline=True)
            embed.add_field(name="Author", value=info['author'].nick, inline=True)
            embed.add_field(name='\u200B', value='\u200B', inline=False)

        await context.send(embed=embed)
        return

    @queue.error
    async def queue_error(self, context: commands.Context, error: commands.CommandError):
        """Handle errors for the queue command."""
        if isinstance(error, commands.errors.CheckFailure):
            await context.send('You do not have the correct role for this command.', delete_after=5)
        # TODO: this isn't messaging the user for some reason. Fix it.
        if isinstance(error, discord.Forbidden):
            await context.author.send(f'This bot does not have the necessary permissions to post in {context.channel}.', delete_after=5)

bot.add_cog(Commands(bot))
bot.run(TOKEN)
