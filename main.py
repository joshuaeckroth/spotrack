# This example requires the 'message_content' intent.

import discord
import json
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import openai
import rich

console = rich.get_console()

creds = json.load(open('creds.json'))

openai_client = openai.OpenAI(api_key=creds['openai']['api_key'])

os.environ['SPOTIPY_CLIENT_ID'] = creds['spotify']['client_id']
os.environ['SPOTIPY_CLIENT_SECRET'] = creds['spotify']['client_secret']

def ask_openai(sys_prompt, user_prompt):
    console.print(f"[bold]System prompt:[/bold] {sys_prompt}")
    console.print(f"[bold]User prompt:[/bold] {user_prompt}")
    chat_completion = openai_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": sys_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        model="gpt-4-turbo-preview",
    )
    response = chat_completion.choices[0].message.content
    console.print(f"[bold]Response:[/bold] {response}")
    return response

spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

sys_prompt_search = """
You are a tool that can create spotify search queries.

Interpret the user's prompt and generate a search query that can be used to search for the user's desired song, artist, or album.

Use the following documentation to help you:

---

You can narrow down your search using field filters. The available filters are album, artist, track, year, upc, tag:hipster, tag:new, isrc, and genre. Each field filter only applies to certain result types.

The artist and year filters can be used while searching albums, artists and tracks. You can filter on a single year or a range (e.g. 1955-1960).
The album filter can be used while searching albums and tracks.
The genre filter can be used while searching artists and tracks.
The isrc and track filters can be used while searching tracks.
The upc, tag:new and tag:hipster filters can only be used while searching albums. The tag:new filter will return albums released in the past two weeks and tag:hipster can be used to return only albums with the lowest 10% popularity.

---

Examples of search queries:

User query: "Find me the album 'The Wall' by Pink Floyd."
Search query: "album:The Wall artist:'Pink Floyd'"

User query: "Find me the song 'Bohemian Rhapsody' by Queen."
Search query: "track:'Bohemian Rhapsody' artist:'Queen'"

VERY IMPORTANT: Return the search query as a string WITHOUT the quotes. RETURN ONLY THE SEARCH STRING.
"""

sys_prompt_response = """
Interpret search results from Spotify based on the user's query.

Add suggestions for follow up searches.
"""

def search_spotify(user_prompt):
    search_string = ask_openai(sys_prompt_search, user_prompt)
    spotify_results = spotify.search(search_string, limit=20)
    console.rule("Spotify results")
    console.print(spotify_results)
    attempts = [search_string]
    while len(spotify_results['tracks']['items']) == 0 and len(attempts) < 4:
        search_string = ask_openai(sys_prompt_search, "These prior attempts failed to produce results, modify them to find the right results:\n\n"+"\n".join(attempts) + "\n\nUser query: " + user_prompt)
        spotify_results = spotify.search(search_string, limit=20)
        console.rule("Spotify results")
        console.print(spotify_results)
        attempts.append(search_string)
    if len(spotify_results['tracks']['items']) == 0:
        return "I'm sorry, I couldn't find any results for your query."
    explanation = ask_openai(sys_prompt_response,
                             "Spotify results:\n\n"+json.dumps(spotify_results) + "\n\n" + \
                             "User query:\n\n" + user_prompt)
    console.print("[bold]Explanation:[/bold] " + explanation)
    return explanation

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

    if message.content.startswith('$spotify '):
        await message.channel.send(search_spotify(message.content[9:]))

client.run(creds['discord_token'])

