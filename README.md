# Example usage

/sp Name some albums by The Beatles

- what happens:

/sp I recommend Get Back by The Beatles for @jane because you love quick songs
equally:
/sp rec Get Back (Beatles) 4 @jane because you love quick songs

(suppose @joe sent the message)

- what happens:
  - The bot will search Spotify for a track called Get Back by The Beatles and return the first result
  - The link to the track will be saved in MongoDB
    - {'recommended_by': 'joe', 'recommended_to': 'jane', 'track': 'Get Back', 'artist': 'The Beatles', 'album': 'Let It Be', 'link': 'https://open.spotify.com/track/4MLBqAEzNN89o2M9h92Z26?si=48651c50d93a4584', 'reason': 'you love quick songs'}

/sp what did @joe recommend to me?
equally:
/sp rec @joe for me
/sp rec @joe @jane

(suppose @jane sent the message)

- what happens:
  - The bot will search MongoDB for all the tracks recommended by joe to jane
  - It will list links to all the tracks



