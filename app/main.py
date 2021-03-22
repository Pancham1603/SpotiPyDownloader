from flask import Flask, render_template, request, url_for, session, redirect, send_file
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
import smtplib
from email.message import EmailMessage

client_id = '***REMOVED***'
client_secret = '***REMOVED***'


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


@app.route('/')
def initiation():
    return render_template("index.html")


@app.route('/checkpoint', methods=['GET', 'POST'])
def check():
    user_data = request.form
    session['name'] = user_data['name']
    session['email'] = user_data['email']
    session['link'] = user_data['link']
    session['number_of_songs'] = user_data['num']
    data = spotify.playlist(link=session['link'], num=session['number_of_songs'])
    songs = []
    for item in range(int(session['number_of_songs'])):
        try:
            track_name = data['items'][item]['track']['name']
            artist_name = data['items'][item]['track']['artists'][0]['name']
            songs.append(f'{track_name} - {artist_name}')
            success = True
        except IndexError:
            pass
        except KeyError:
            print("-------------------------------------------")
            print("Please input a valid Spotify Playlist link!")
            print("-------------------------------------------")
            success = False
            break
    if success:
        directory = f"{session['name']}'s Playlist"
        session['directory'] = directory
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
            except KeyError:
                print(f"Downloading: {song}")
                result = YoutubeSearch(song, max_results=1).to_dict()
                suffix = result[0]['url_suffix']
                link = base + suffix
                out_file = YouTube(link).streams.filter(only_audio=True).first().download(directory)
                base, ext = os.path.splitext(out_file)
                new_file = base + '.mp3'
                os.rename(out_file, new_file)
            except FileExistsError:
                pass
        file_paths = []

        for root, directories, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                file_paths.append(filepath)

        with ZipFile(f"{session['name']}'s Playlist\{session['name']}'s Playlist.zip", 'w') as zip:
            for file in file_paths:
                zip.write(file)

        print("--------------------------------")
        print('All files zipped successfully!')
        print("--------------------------------")
        print("Thankyou for using this service!")
        print("Made with ❤️ by Pancham Agarwal")
        print("--------------------------------")
    return redirect('/download')


@app.route('/download', methods=['GET', 'POST'])
def download():
    file_path = f"{session['directory']}\{session['directory']}.zip"
    return_data = io.BytesIO()
    with open(file_path, 'rb') as fo:
        return_data.write(fo.read())
    return_data.seek(0)
    message = EmailMessage()
    message['subject'] = 'Feedback - Spotify Downloader'
    message['from'] = '***REMOVED***'
    message['to'] = session['email']
    html_message = open('app\mail.html').read()
    message.add_alternative(html_message, subtype='html')
    password = "***REMOVED***"
    with smtplib.SMTP_SSL('smtp.gmail.com', 465)as smtp:
        smtp.login(message['from'], password)
        smtp.send_message(message)

    shutil.rmtree(f"{session['directory']}")
    return send_file(return_data, mimetype='application/zip', as_attachment=True,
                     attachment_filename=f"{session['name']}'s Playlist.zip")
