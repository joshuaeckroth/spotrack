# This example requires the 'message_content' intent.

import discord
import json
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import openai
import rich
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

console = rich.get_console()

creds = json.load(open('creds.json'))

mongodb_client = MongoClient(creds['mongodb']['url'], server_api=ServerApi('1'))
try:
    mongodb_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

openai_client = openai.OpenAI(api_key=creds['openai']['api_key'])

os.environ['SPOTIPY_CLIENT_ID'] = creds['spotify']['client_id']
os.environ['SPOTIPY_CLIENT_SECRET'] = creds['spotify']['client_secret']

def ask_openai(sys_prompt, user_prompt, return_json=False):
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
        response_format=({"type": "json_object"} if return_json else None)
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
    spotify_results = spotify.search(search_string, limit=5)
    console.rule("Spotify results")
    console.print(spotify_results)
    attempts = [search_string]
    while len(spotify_results['tracks']['items']) == 0 and len(attempts) < 4:
        search_string = ask_openai(sys_prompt_search, "These prior attempts failed to produce results, modify them to find the right results:\n\n"+"\n".join(attempts) + "\n\nUser query: " + user_prompt)
        spotify_results = spotify.search(search_string, limit=5)
        console.rule("Spotify results")
        console.print(spotify_results)
        attempts.append(search_string)
    tracks = []
    for t in spotify_results['tracks']['items']:
        track = {
            "name": t['name'],
            "artist": t['artists'][0]['name'],
            "album": t['album']['name'],
            "release_date": t['album']['release_date'],
            "popularity": t['popularity'],
            "preview_url": t['preview_url'],
            "spotify_url": t['external_urls']['spotify']
        }
        tracks.append(track)
    return tracks
        
    #if len(spotify_results['tracks']['items']) == 0:
    #    return "I'm sorry, I couldn't find any results for your query."
    #explanation = ask_openai(sys_prompt_response,
    #                         "Spotify results:\n\n"+json.dumps(spotify_results) + "\n\n" + \
    #                         "User query:\n\n" + user_prompt)
    #console.print("[bold]Explanation:[/bold] " + explanation)
    #return explanation

sys_prompt_recognize_action = """
You are a bot that recognizes the action a user wants to take based on their prompt in Discord.

There are three possible actions a user can take: recommend a track to a user, get recommendations that have been, or search spotify for information.

Return JSON. Example formats are given below.

Examples of user prompts and responses:

---

From: joe
User prompt: I recommend Get Back by The Beatles for @jane because you love quick songs
Response: {"action": "recommend", "track": "Get Back", "artist": "The Beatles", "recipient": "jane", "reason": "you love quick songs", "recommender": "joe"}

---

From: joe
User prompt: rec Get Back (Beatles) 4 @jane because she loves quick songs
Response: {"action": "recommend", "track": "Get Back", "artist": "The Beatles", "recipient": "jane", "reason": "she loves quick songs", "recommender": "joe"}

---

From: jane
User prompt: what did @joe recommend to me?
Response: {"action": "get_recommendations", "recipient": "jane", "recommender": "joe"}

---

From: jane
User prompt: rec @joe for me
Response: {"action": "get_recommendations", "recipient": "jane", "recommender": "joe"}

---

From: jane
User prompt: my recs
Response: {"action": "get_recommendations", "recipient": "jane"}

---

From: jane
User prompt: rec @joe @jane
Response: {"action": "get_recommendations", "recipient": "jane", "recommender": "joe"}

---

From: jane
User prompt: what did I recommend?
Response: {"action": "get_recommendations", "recommender": "jane"}

---

From: jane
User prompt: who recommended Get Back?
Response: {"action": "get_recommendations", "track": "Get Back"}

---

From: bob
User prompt: Name some albums by The Beatles
Response: {"action": "search_spotify", "query": "album: The Beatles"}
"""

def recognize_action(from_user, user_prompt):
    action = ask_openai(sys_prompt_recognize_action, f"From: {from_user}\nUser prompt: {user_prompt}",
                        True)
    return json.loads(action)

def save_recommendation(action):
    if 'recommender' not in action or 'recipient' not in action:
        return False
    if 'track' not in action and 'artist' not in action:
        return False
    if 'track' in action and 'artist' not in action:
        spotify_tracks = search_spotify(f"track: '{action['track']}'")
    elif 'track' not in action and 'artist' in action:
        spotify_tracks = search_spotify(f"artist: '{action['artist']}'")
    else:
        spotify_tracks = search_spotify(f"track: '{action['track']}' artist: '{action['artist']}'")
    recommendation = {
        "recommender": action['recommender'],
        "recipient": action['recipient'],
        "track": action['track'] if 'track' in action else None,
        "artist": action['artist'] if 'artist' in action else None,
        "reason": action['reason'] if 'reason' in action else None,
        "spotify": spotify_tracks
    }
    mongodb_client.spotrack.recommendations.insert_one(recommendation)
    return True

def get_recommendations(action):
    if 'recommender' in action and 'recipient' in action:
        recommendations = list(mongodb_client.spotrack.recommendations.find({"recommender": action['recommender'], "recipient": action['recipient']}))
    elif 'recommender' in action:
        recommendations = list(mongodb_client.spotrack.recommendations.find({"recommender": action['recommender']}))
    elif 'recipient' in action:
        recommendations = list(mongodb_client.spotrack.recommendations.find({"recipient": action['recipient']}))
    else:
        recommendations = []
    return recommendations

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
    if message.content.startswith('/sp '):
        #await message.channel.send(search_spotify(message.content[4:]))
        action = recognize_action(message.author.name, message.content[4:])
        if action['action'] == 'recommend':
            result = save_recommendation(action)
            if result:
                await message.channel.send("I saved your recommendation.")
            else:
                await message.channel.send("I'm sorry, I couldn't save your recommendation.")
        elif action['action'] == 'get_recommendations':
            recommendations = get_recommendations(action)
            if len(recommendations) == 0:
                await message.channel.send("I'm sorry, I couldn't find any recommendations.")
            else:
                for recommendation in recommendations:
                    await message.channel.send(recommendation)
        else:
            await message.channel.send(action)

client.run(creds['discord_token'])

