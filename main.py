# This example requires the 'message_content' intent.

import discord
import json
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

creds = json.load(open('creds.json'))

os.environ['SPOTIPY_CLIENT_ID'] = creds['spotify']['client_id']
os.environ['SPOTIPY_CLIENT_SECRET'] = creds['spotify']['client_secret']

spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

birdy_uri = 'spotify:artist:2WX2uTcsvV5OnS0inACecP'
results = spotify.artist_albums(birdy_uri, album_type='album')
albums = results['items']
while results['next']:
    results = spotify.next(results)
    albums.extend(results['items'])
for album in albums:
    print(album['name'])

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')


client.run(creds['discord_token'])

