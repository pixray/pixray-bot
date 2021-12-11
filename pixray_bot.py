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
        self.uuids = {}

    @commands.command(name='create')
    @commands.has_role('attendee')
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
        embed = discord.Embed(
            title="Getting started!",
            color=0x4168B5
        )
        embed.add_field(name="Query", value=query, inline=False)
        embed.add_field(name="UUID", value=uuid, inline=False)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Error", value=error, inline=True)
        print(f'New session started ({uuid}) with status {status} and error {error}')
        await context.send(embed=embed, delete_after=10)

        # Retain memory of query since multiple queries can be simultaneously sent
        self.uuids[uuid] = {
            'query': query,
            'status': status,
            'error': error,
            'author': context.author
        }

        poll_url = f'{POLL_API}/{uuid}'

        t = 0
        while (status == 'queued' or status == 'processing') and (error == None):
            if t == 0:
                # await context.send(f'Generating... Query -> \"{query}\". ID -> {uuid}. Status -> {status}.')
                embed = discord.Embed(
                    title="Generating 🌱",
                    color=0x4168B5
                )
                embed.add_field(name="Query", value=query, inline=False)
                embed.add_field(name="UUID", value=uuid, inline=False)
                embed.add_field(name="Status", value=status, inline=True)
                embed.add_field(name="Error", value=error, inline=True)
                await context.send(embed=embed)
            await asyncio.sleep(5)
            r = requests.get(poll_url)
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
        response = requests.get(out_url, stream=True)

        # Delete uuid from dictionary after successful generation
        deleted_uuid = self.uuids.pop(uuid, None)

        with open(OUTFILE, 'wb') as handle:
            for data in tqdm(response.iter_content()):
                handle.write(data)

        print(f'Download complete, data saved in {OUTFILE}')
        file = discord.File(OUTFILE, filename=OUTFILE)
        embed = discord.Embed(
            title="Generation complete 🪴",
            color=0x4168B5
        )
        embed.add_field(name="Query", value=query, inline=False)
        embed.add_field(name="UUID", value=uuid, inline=False)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Error", value=error, inline=True)
        embed.set_image(url=f"attachment://{OUTFILE}")
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
    @commands.has_role('attendee')
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

        query = self.uuids[uuid]['query']
        status = self.uuids[uuid]['status']
        error = self.uuids[uuid]['error']
        embed = discord.Embed(
            color=0x4168B5
        )
        embed.add_field(name="Query", value=query, inline=False)
        embed.add_field(name="UUID", value=uuid, inline=False)
        embed.add_field(name="Status", value=status, inline=True)
        embed.add_field(name="Error", value=error, inline=True)
        await context.send(embed=embed, delete_after=10)
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

bot.add_cog(Commands(bot))
bot.run(TOKEN)
