import json
import os
import re

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyPKCE

youtube_scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
spotify_scopes = "playlist-modify-private"
channel_id = "UC5SgY4afhff1rLuyTKGo-Wg"
spotify_user_id = "panthernz"

# https://developers.google.com/youtube/v3/docs/playlistItems/list
# https://developers.google.com/youtube/v3/docs/playlists/list

def remove_block(text:str, search:str):
    idx = 0
    while True:
        f = text.find(search[0], idx)
        if f != -1:
            l = text.find(search[1], f)
            if l != -1:
                new_text = text[idx:f] + text[l+1:]
                text = new_text
            else:
                break
        else:
            break     
    return text

def main():
    try:
        youtube_secret = json.load(open("youtube_client.json"))["client_secret"]
    except IOError:
        print('Failed to load youtube_client.json')
        return

    try:
        spotify_json = json.load(open("spotify_client.json"))
        spotify_secret = spotify_json["client_secret"]
        spotify_id = spotify_json["client_id"]
    except IOError:
        print('Failed to load spotify_client.json')
        return

    print('client secrets loaded, initialising youtube api')
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=youtube_secret)

    print('Loading youtube playlists')
    request = youtube.playlists().list(part="snippet,contentDetails", maxResults=50, channelId=channel_id)

    response = request.execute()

    playlists = []
    while request is not None:
        response = request.execute()
        for item in response["items"]:
            playlists.append((item["snippet"]["title"], item["id"]))
        request = youtube.playlists().list_next(request, response)

    while True:
        print('Select playlist:')
        print(', '.join([title for title, _ in playlists]))
        selected = input()
        youtube_playlist_id = 0
        for title, pid in playlists:
            if title == selected:
                youtube_playlist_id = pid
                break

        print('Loading youtube playlist items')
        request = youtube.playlistItems().list(part="snippet,contentDetails", maxResults=50, playlistId=youtube_playlist_id)

        response = request.execute()

        playlist_entries = []
        while request is not None:
            response = request.execute()
            for item in response["items"]:
                playlist_entries.append((item["snippet"]["title"], item["contentDetails"]["videoId"]))
            request = youtube.playlistItems().list_next(request, response)

        print(f'Playlist Size: {len(playlist_entries)}')
        print('Loading spotify api with auth')
        #sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=spotify_id, client_secret=spotify_secret))
        sp = spotipy.Spotify(auth_manager=SpotifyPKCE(client_id=spotify_id, redirect_uri='https://www.alexdenford.com/', scope=spotify_scopes))

        print('Auth request sent')
        spotify_tracks = []

        result_fmt = '{}\t\t\t->\t\t\t{}'

        print('Requesting / searching spotify tracks')
        for title, video_id in playlist_entries:
            if 'Deleted video' in title:
                continue

            if '-' not in title:
                # find channel now from the video id
                video = youtube.videos().list(part="snippet", id=video_id, maxResults=1).execute()
                if len(video['items']) != 0:
                    channel_title = video['items'][0]['snippet']['channelTitle']
                    title = f'{channel_title} - {title}'

            pre_regex = title
            title = remove_block(remove_block(remove_block(remove_block(title, "【】"), "{}"), "()"), "[]")
            title = re.sub('- Topic', '', title, re.IGNORECASE)
            title = re.sub('Official Video', '', title, re.IGNORECASE)
            title = re.sub('Official Music Video', '', title, re.IGNORECASE)
            title = re.sub(' & ', ' ', title)
            
            ft_idx = title.lower().find(' ft.')
            if ft_idx == -1:
                ft_idx = title.lower().find(' ft ')

            if ft_idx != -1:
                end_idx = min(title.find('-', ft_idx), title.find('.', ft_idx))
                new_title = title[:ft_idx] + '' if end_idx == -1 else title[end_idx+1:]
                title = new_title

            if len(title) == 0:
                print(result_fmt.format(pre_regex, 'NO MATCH FOUND (NULL SEARCH TERM)'))
                continue

            results = sp.search(q=title, limit=1)
            for item in results['tracks']['items']:
                spotify_tracks.append(item['id'])
                print(result_fmt.format(title, '{} - {}'.format(', '.join([x['name'] for x in item['artists']]), item['name'])))

            if len(results['tracks']['items']) == 0:
                print(result_fmt.format(title, 'NO MATCH FOUND'))

        # create playlist
        print(f'Total matches found: {len(spotify_tracks)}')
        print('Creating spotify playlist')
        playlist = sp.user_playlist_create( user=spotify_user_id, name=f'Youtube - {selected}', public=False)

        print('Adding tracks to spotify playlist')
        for i in range(0,len(spotify_tracks),99):
            sp.user_playlist_add_tracks(user=spotify_user_id, playlist_id=playlist['id'], tracks=spotify_tracks[i:min(i + 99, len(spotify_tracks) - 1)])

        print('Complete\n')

if __name__ == "__main__":
    main()



        #if use_authentication:
    #    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file("credentials.json", scopes)
    #    credentials = flow.run_console()
    #    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
    #    request = youtube.playlists().list(part="snippet,contentDetails", maxResults=50, mine=True)
    #else:
