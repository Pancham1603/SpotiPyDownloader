from flask import Flask, render_template, request, url_for, session, redirect, send_file, flash
import smtplib
import base64
import requests
import datetime
from urllib.parse import urlencode
from pytube import YouTube
from youtube_search import YoutubeSearch
import os
from zipfile import ZipFile
import io
import shutil
from email.message import EmailMessage
import pymongo
from pymongo import MongoClient
import asyncio
import gridfs
import random

client_id = '***REMOVED***'
client_secret = '***REMOVED***'

client = MongoClient(
    "***REMOVED***")
db = client.test
fs = gridfs.GridFS(db)
collection1 = ***REMOVED***
collection2 = ***REMOVED***
collection3 = db['downloaded_files']

class SpotifyAPI(object):
    access_token = None
    access_token_expires = datetime.datetime.now()
    access_token_did_expire = True
    client_id = None
    client_secret = None
    token_url = 'https://accounts.spotify.com/api/token'

    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret

    def get_client_credentials(self):
        """
        Returns a base64 encoded string
        """
        client_id = self.client_id
        client_secret = self.client_secret
        if client_secret == None or client_secret == None:
            raise Exception('You must set client_ID and client_secret')
        client_creds = f'{client_id}:{client_secret}'
        client_creds_base64 = base64.b64encode(client_creds.encode())
        return client_creds_base64.decode()

    def get_token_headers(self):
        client_creds_base64 = self.get_client_credentials()
        return {
            'Authorization': f'Basic {client_creds_base64}'
        }

    def get_token_data(self):
        return {
            'grant_type': 'client_credentials'
        }

    def perfom_auth(self):
        token_url = self.token_url
        token_data = self.get_token_data()
        token_headers = self.get_token_headers()
        r = requests.post(token_url, data=token_data, headers=token_headers)
        if r.status_code not in range(200, 299):
            raise Exception("Could not authenticate client.")
        now = datetime.datetime.now()
        data = r.json()
        access_token = data['access_token']
        expires_in = data['expires_in']
        expires = now + datetime.timedelta(seconds=expires_in)
        self.access_token_expires = expires
        self.access_token_did_expire = expires < now
        self.access_token = access_token
        return True

    def get_access_token(self):
        token = self.access_token
        expires = self.access_token_expires
        now = datetime.datetime.now()
        if expires < now:
            self.perfom_auth()
            return self.get_access_token()
        elif token == None:
            self.perfom_auth()
            return self.get_access_token()
        return token

    def search(self, query, search_type='artist'):
        access_token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        endpoint = 'https://api.spotify.com/v1/search'
        data = urlencode({
            'q': query,
            'type': search_type.lower()
        })
        print(data)
        lookup_url = f"{endpoint}?{data}"
        r = requests.get(lookup_url, headers=headers)
        print(lookup_url)
        if r.status_code not in range(200, 299):
            return {}
        return r.json()

    def playlist(self, link, num, search_type='playlist'):
        link_main = link[34:]
        target_URI = ''
        for char in link_main:
            if char != '?':
                target_URI += char
            else:
                break
        access_token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        endpoint = 'https://api.spotify.com/v1/playlists/'
        append = f"/tracks?market=IN&fields=items(track(name%2Cartists))&limit={num}&offset=0"
        lookup_url = f"{endpoint}{target_URI}{append}"
        r = requests.get(lookup_url, headers=headers)
        if r.status_code not in range(200, 299):
            return {}
        return r.json()

spotify = SpotifyAPI(client_id, client_secret)

while True:
    queue = collection2.find()
    for user in queue:
        data = spotify.playlist(link=user['link'], num=user['length_req'])
        songs = []
        for item in range(int(user['length_req'])):
            try:
                track_name = data['items'][item]['track']['name']
                artist_name = data['items'][item]['track']['artists'][0]['name']
                songs.append(f'{track_name} - {artist_name}')
                success = True
            except IndexError:
                pass
        directory = f"{user['name']}'s Playlist"
        user['directory'] = directory
        try:
            os.mkdir(directory)
        except:
            shutil.rmtree(directory)
            os.mkdir(directory)
        base = 'https://www.youtube.com'

        for song in songs:
            try:
                print(f"Downloading: {song}")
                result = YoutubeSearch(song, max_results=1).to_dict()
                suffix = result[0]['url_suffix']
                link = base + suffix
                out_file = YouTube(link).streams.filter(only_audio=True).first().download(directory)
                base, ext = os.path.splitext(out_file)
                new_file = base + '.mp3'
                os.rename(out_file, new_file)
                asyncio.sleep(10)
            except KeyError:
                print(f"Downloading: {song}")
                result = YoutubeSearch(song, max_results=1).to_dict()
                suffix = result[0]['url_suffix']
                link = base + suffix
                out_file = YouTube(link).streams.filter(only_audio=True).first().download(directory)
                base, ext = os.path.splitext(out_file)
                new_file = base + '.mp3'
                os.rename(out_file, new_file)
                asyncio.sleep(10)
            except FileExistsError:
                pass
            except:
                print(f"Download Failed: {song}")
                asyncio.sleep(10)
        file_paths = []

        for root, directories, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                file_paths.append(filepath)

        with ZipFile(f"app\playlists\{user['email']}.zip", 'w') as zip:
            for file in file_paths:
                zip.write(file)
        zip_path = fs.put(f"playlists\{user['email']}.zip",filename=f"{user['email']}.zip",encoding='utf-8')
        collection3.insert_one(
            {
                'name':user['name'],
                'email':user['email'],
                'otp':user['otp'],
                'playlist_path':zip_path,
                'time':datetime.datetime.now()
            }
        )

        collection2.delete_one(
            {
                'name':user['name'],
                'email':user['email'],
                'link':user['link'],
                'length_req':user['length_req'],
                'otp':user['otp']
            }
        )
        print(f"Playlist for {user['name']} downloaded successfully!")
        shutil.rmtree(directory)
