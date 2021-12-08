import discord

TOKEN = 'OTE2ODY4NTI0NDczOTkxMTg5.YawaWg.Hu-SJPvwMrpRkFVaUClZsPJrTrQ'

client = discord.Client()

@client.event
async def on_ready():
    print('We have successfully loggged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower() == 'pixray/hello':
        await message.channel.send(f'Hello, {message.author.display_name}!')
        return

    if message.content.lower() == 'pixray/bye':
        await message.channel.send(f'See you later, {message.author.display_name}!')
        return

client.run(TOKEN)
