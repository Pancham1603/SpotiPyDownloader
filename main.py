from flask import Flask, render_template, request, url_for, session, redirect, send_file, flash, send_from_directory
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
import random
import json

client_id = '***REMOVED***'
client_secret = '***REMOVED***'

client = pymongo.MongoClient(
    "***REMOVED***")
db = client.test
collection1 = ***REMOVED***
collection2 = ***REMOVED***


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


app = Flask(__name__)
app.secret_key = 'demo'
spotify = SpotifyAPI(client_id, client_secret)


@app.route('/home')
@app.route('/')
def initiation():
    return render_template("index.html")


@app.route('/queuedownload', methods=['GET', 'POST'])
def queueDownload():
    user_data = request.form
    session['name'] = user_data['name']
    session['email'] = user_data['email']
    session['link'] = user_data['link']
    session['num'] = user_data['num']
    results = collection1.find({'email': session['email'].lower()})
    data = spotify.playlist(link=session['link'], num=session['num'])
    songs = []
    for item in range(int(session['num'])):
        try:
            track_name = data['items'][item]['track']['name']
            artist_name = data['items'][item]['track']['artists'][0]['name']
            songs.append(f'{track_name} - {artist_name}')
            success = True
        except IndexError:
            pass
        except KeyError:
            success = False
            break
    if success:
        if results.count() == 0:

            collection1.insert_one({
                'name': session['name'],
                'email': session['email'].lower(),
                'request': {
                    'playlist': session['link'],
                    'length_req': session['num'],
                    'time': datetime.datetime.now()
                },
                'uses': 1
            })

            collection2.insert_one(
                {
                    'name': session['name'],
                    'email': session['email'],
                    'link': session['link'],
                    'length_req': session['num'],
                }
            )
            flash(f"""Download queued! You'll receive a download link on your e-mail within 10minutes.""")
            return redirect('/')
        elif results.count() != 0:
            for result in results:
                use = result['uses'] + 1

            document = {'$set':
                {f'request{use}': {
                    'playlist': session['link'],
                    'length_req': session['num'],
                    'time': datetime.datetime.now()
                },
                    'uses': use}
            }

            query = {'email': session['email']}
            collection1.update_one(query, document)
            collection2.insert_one(
                {
                    'name': session['name'],
                    'email': session['email'],
                    'link': session['link'],
                    'length_req': session['num']
                }
            )
            flash(f"""Download queued! You'll receive a download link on your e-mail within 10minutes.""")
            return redirect('/')
    else:
        flash("Enter a valid Spotify Playlist URL!")
        return redirect('/')


@app.route('/download/<path:filename>')
def custom_static(filename):
    try:
        email = filename[:-4]
        email = email.lower()
        print(email)
        user = collection3.find_one(
            {
                'email': email
            }
        )
        print(user)
        file_url = user['url']
        directory = user['directory']
        os.remove(f"{user['email']}.zip")
        shutil.rmtree(directory)
        collection3.delete_one(
            {
                'email': filename[:-4],
            }
        )

        # https://drive.google.com/file/d/here/view?usp=sharing
        return redirect(file_url)
    except:
        return redirect(file_url)

@app.route("/***REMOVED***")
def verif():
    return render_template("***REMOVED***")

@app.errorhandler(404)
def error(error):
    return render_template('error404.html')


@app.errorhandler(500)
def error(error):
    return render_template('error500.html')


@app.errorhandler(502)
def error(error):
    return render_template('error502.html')
