import requests
from bs4 import BeautifulSoup
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import json
import pprint
import time
import re;
import jsonlines

SPOTIPY_CLIENT_ID=""
SPOTIPY_CLIENT_SECRET=''
SPOTIPY_REDIRECT_URI="http://127.0.0.1:9090"
SCOPE = "ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing app-remote-control streaming playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public user-follow-modify user-follow-read user-read-playback-position user-top-read user-read-recently-played user-library-modify user-library-read user-read-email user-read-private"


def print(str):
    pprint.pprint(str)

def getSpotifyArtists(additionalPlaylists):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope=SCOPE))
    
    artists = {}
    addFromPlaylists(sp, artists)
    addFromLikedSongs(sp, artists)

    artistsByName = {}
    for id, data in artists.items():
        if data[0] in artistsByName:
            artistsByName[data[0]].update(data[1])
        else:
            artistsByName[data[0]] = data[1]
    return artistsByName
    
def addFromLikedSongs(sp, artists):
    count = 20
    times = 0
    total = 0
    while count == 20:
        start = count * times
        try:
            likedSongs = sp.current_user_saved_tracks(offset=start)
        except:
            break
        times += 1
        count = 0
        for track in likedSongs['items']:
            trackName = track["track"]["name"]
            trackId = track["track"]["id"]
            trackArtists = track["track"]["artists"]
            for trackArtist in trackArtists:
                id = trackArtist['id']
                name = trackArtist['name']
                if id not in artists:
                    artists[id] = (name, {})
                if trackId not in artists[id][1]:
                    artists[id][1][trackId] = (trackName, set())
                artists[id][1][trackId][1].add("Liked Songs")
            count += 1
            total += 1

def addFromPlaylists(sp, artists):
    username = sp.current_user()['id']
    playlistIds = []
    count = 50
    times = 0
    total = 0
    while count == 50:
        start = count * times
        try:
            userPlaylists = sp.current_user_playlists(offset=start)
        except:
            break
        times += 1
        count = 0
        for item in userPlaylists['items']:
            if item['owner']['id'] == username or item["name"] in additionalPlaylists:
                playlistIds.append((item['id'], item['name']))
            count += 1
            total += 1
    for id, name in playlistIds:
        addAllArtists(sp, id, name, artists)
        

def addAllArtists(sp, id, playlistName, artists):
    count = 100
    times = 0
    total = 0
    while count == 100:
        start = count * times 
        try:
            tracks = sp.playlist_tracks(id, offset=start)
        except:
            break
        times += 1
        count = 0
        for track in tracks["items"]:
            count += 1
            total += 1
            trackName = track["track"]["name"]
            trackId = track["track"]["id"]
            trackArtists = track["track"]["artists"]
            for trackArtist in trackArtists:
                id = trackArtist['id']
                name = trackArtist['name']
                if id not in artists:
                    artists[id] = (name, {})
                if trackId not in artists[id][1]:
                    artists[id][1][trackId] = (trackName, set())
                artists[id][1][trackId][1].add(playlistName)




def getEvents():
    baseUrl = "https://edmtrain.com"
    timeZoneId = "America%2FNew_York"
    resultsAttributes = "includeElectronic=true&includeOther=false"
    locations = [86]
    requestUrl = '{}/get-events?'.format(baseUrl)
    for location in locations:
        requestUrl += 'locationIdArray%5B%5D={}&'.format(location)
    
    requestUrl += resultsAttributes
    requestUrl += '&timeZoneId={}'.format(timeZoneId)

    response = requests.get(requestUrl)
    print(response.status_code)
    # print(response.content)
    parsed_html = BeautifulSoup(response.content)
    return parsed_html.find_all('div', attrs={'class':'eventContainer'})

    

def parseEvents(events):

    eventsByArtist = {}
    eventsByDate = {}
    

    for event in events:
        titlestr = event.get("titlestr")
        venue = event.get("venue")
        date = event.get("sorteddate")
        if (date not in eventsByDate):
            eventsByDate[date] = set()
        splitTitleStr = re.split(',|:|b2b', titlestr)
        for elm in splitTitleStr:
            artistStripped = elm.strip()
            if (artistStripped not in eventsByArtist):
                eventsByArtist[artistStripped] = set()
            eventsByDate[date].add((artistStripped, venue))
            eventsByArtist[artistStripped].add((venue, date))
    return eventsByArtist, eventsByDate

def merge(eventsByDate, importantArtists):
    jsonResult = {}
    for date, events in eventsByDate.items():
        printed = False
        for event in events:
            artist = event[0]
            venue = event[1]
            if artist in importantArtists.keys():
                if not printed:
                    jsonResult[date] = {}
                    printed = True
                if artist not in jsonResult[date]:
                    jsonResult[date][artist] = {"venues": [], "songs": {}}
                jsonResult[date][artist]["venues"].append(venue)
                jsonSongs = jsonResult[date][artist]["songs"]
                songs = importantArtists[artist]
                for songid, songData in songs.items():
                    songName = songData[0]
                    songOrginPlaylist = songData[1]
                    if songName not in jsonSongs:
                        jsonSongs[songName] = []
                    if (songOrginPlaylist not in jsonSongs[songName]):
                        jsonSongs[songName] += songOrginPlaylist
    with jsonlines.open('output.json', mode='w') as writer:
        writer.write(jsonResult)
                
     

if __name__ == "__main__":

    url = "https://edmtrain.com/get-events?locationIdArray%5B%5D=86&includeElectronic=true&includeOther=false&timeZoneId=America%2FNew_York"
    eventsByArtist, eventsByDate = parseEvents(getEvents())
    additionalPlaylists = set()
    # print(eventsByDate)
    importantArtists = getSpotifyArtists(additionalPlaylists)
    # print(importantArtists)
    merge(eventsByDate, importantArtists)
