import base64
import datetime
import os
import shutil
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode
from zipfile import ZipFile

import requests
import youtube_dl
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pymongo import MongoClient
from youtube_search import YoutubeSearch

# import eyed3

gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

client_id = ''
client_secret = ''

client = MongoClient(
    "")
db = client.
collection1 = db['']
collection2 = db['']
collection3 = db['']


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

    def playlist(self, link, num, offset):
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
        append = f"/tracks?market=ES&fields=items(track(name,artists,album(name,images)))&limit={num}&offset={offset}"
        lookup_url = f"{endpoint}{target_URI}{append}"
        r = requests.get(lookup_url, headers=headers)
        if r.status_code not in range(200, 299):
            return {}
        return r.json()


spotify = SpotifyAPI(client_id, client_secret)

while True:
    queue = collection2.find()
    for user in queue:
        user_check = collection1.find_one(
            {
                'email': user['email'].lower(),
                'uses': 1
            }
        )
        print(f"Download starting: {user['name']} {user['length_req']}")
        num = int(user['length_req'])
        if num > 100:
            songs = []
            images = []
            album_names = []
            artist_names = []
            track_names = []
            loops_req = int(user['length_req']) // 100 + 1
            offset = 0
            for loop in range(loops_req):
                data = spotify.playlist(link=user['link'], num=100, offset=offset)
                for item in range(100):
                    try:
                        none_object = data['items'][item]['track']
                    except IndexError:
                        pass
                    if none_object == None:
                        pass
                    else:
                        try:
                            track_name = data['items'][item]['track']['name']
                            artist_name = data['items'][item]['track']['artists'][0]['name']
                            image = data['items'][item]['track']['album']['images'][1]['url']
                            album_name = data['items'][item]['track']['album']['name']
                            songs.append(f'{track_name} - {artist_name}')
                            images.append(image)
                            album_names.append(album_name)
                            artist_names.append(artist_name)
                            track_names.append(track_name)
                            success = True
                        except IndexError:
                            pass
                offset += 100
        else:
            songs = []
            images = []
            album_names = []
            artist_names = []
            track_names = []
            data = spotify.playlist(link=user['link'], num=num, offset=0)
            for item in range(num):
                try:
                    track_name = data['items'][item]['track']['name']
                    artist_name = data['items'][item]['track']['artists'][0]['name']
                    image = data['items'][item]['track']['album']['images'][1]['url']
                    album_name = data['items'][item]['track']['album']['name']
                    songs.append(f'{track_name} - {artist_name}')
                    images.append(image)
                    album_names.append(album_name)
                    artist_names.append(artist_name)
                    track_names.append(track_name)
                    success = True
                except IndexError:
                    pass
        directory = f"{user['email'].lower()}'s Playlist"
        user['directory'] = directory
        try:
            os.mkdir(directory)
        except:
            try:
                shutil.rmtree(directory)
                os.mkdir(directory)
            except:
                pass
        base = 'https://www.youtube.com'
        for song in songs:
            index = songs.index(song)
            success = False
            try:



                print(f"Downloading: {song}")
                result = YoutubeSearch(song, max_results=1).to_dict()
                suffix = result[0]['url_suffix']
                link = base + suffix
                song = "".join(x for x in song if (x.isalnum() or x in "._- "))
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': f'{directory}/{song}.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([link])
                # success = True
            except FileExistsError:
                # success = True
                pass
            except:
                try:
                    print(f"Downloading again: {song}")
                    result = YoutubeSearch(song, max_results=1).to_dict()
                    suffix = result[0]['url_suffix']
                    link = base + suffix
                    song = "".join(x for x in song if (x.isalnum() or x in "._- "))
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': f'{directory}/{song}.%(ext)s',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                    }
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([link])
                except:
                    print(f"Download failed: {song}")
            # if success:
            #     audiofile = eyed3.load(f"{directory}\{song}.mp3")
            #     audiofile.tag.artist = artist_names[index]
            #     audiofile.tag.album = album_names[index]
            #     audiofile.tag.title = track_names[index]
            #     audiofile.tag.track_num = int(index+1)
            #     audiofile.tag.images = images[index]
            #     audiofile.tag.save()

        print(f"Playlist for {user['name']} downloaded successfully!")
        file_paths = []

        for root, directories, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                file_paths.append(filepath)
        with ZipFile(f"{user['email'].lower()}.zip", 'w') as zip:
            for file in file_paths:
                zip.write(file)

        file = drive.CreateFile(
            {
                'title': f"{user['email'].lower()}.zip",
                'parents': [{'kind': 'drive#fileLink',
                             'id': ""}]
            }
        )
        file.SetContentFile(f"{user['email'].lower()}.zip")
        file.Upload()
        file_id = file['id']

        file_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        file.content.close()
        name = user['name']
        print("Upload complete")
        collection2.delete_one(
            {
                'name': user['name'],
                'email': user['email'].lower(),
                'link': user['link'],
                'length_req': user['length_req']
            }
        )

        message = EmailMessage()
        message['subject'] = 'Download Complete - SpotiPy Downloader'
        message['from'] = ''
        message['to'] = user['email'].lower()
        html_message = """
<!DOCTYPE html>
<html lang='en' class=''>

<head>

<meta charset='UTF-8'>

<meta name="robots" content="noindex">


<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Montserrat:400,700">
<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto+Condensed">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/normalize/5.0.0/normalize.min.css">

<style class="INLINE_PEN_STYLESHEET_ID" >
*, *:before, *:after {
box-sizing: border-box;
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
}

body {
font-size: 12px;
}

body, button, input {
font-family: 'Montserrat', sans-serif;
font-weight: 700;
letter-spacing: 1.4px;
}

h1 {
font-family: 'Montserrat', sans-serif;
font-weight: 700;
letter-spacing: 1.4px;
text-align: center;
font-size: 30px;
color: #1db954;
}

p {
text-align: center;
line-height: 17px;
}

a {
color: rgb(66, 71, 77);
}

button {
color: #1db954;
background-color: rgb(66, 71, 77);
}

.form {
text-align: center;
align-items: center;
padding-top: 10px;
}

.note {
    color: red;
}
</style>
"""
        html_message += f"""   
<script src="https://cpwebassets.codepen.io/assets/common/stopExecutionOnTimeout-157cd5b220a5c80d4ff8e0e70ac069bffd87a61252088146915e8726e5d9f147.js"></script>
<script  src="https://cdpn.io/cp/internal/boomboom/pen.js?key=pen.js-00245fc6-a69f-7fef-45f8-9ca6a7d058a6" crossorigin></script>
<body>
<h1 cl#ass="heading">SpotiPy Downloader</h1>
<p>Download Link: <a href="{file_url}">{file_url}</a> </p>
<p>The file will be available on the above link for 24hours.</p>
<p>Hey {name.title()}! Your playlist is read Thank you for using SpotiPy Downloader. I'd love to know how you found the <br>experience of using the service so would like to invite you to rate on <a href="https://forms.gle/33zWczLqooorKUiA8">Google Forms</a><br> - it'll only take a few clicks and will be invaluable to me!
</p>
<div class="form">
<form action="https://forms.gle/33zWczLqooorKUiA8">
    <button type="submit">FEEDBACK FORM</button>
</form>
<p>ZipFile support link: <a href="https://docs.google.com/document/d/1hWC_WXkM7LTVKbOCcIcA76YJjdG3dom78GVXhPqRWf0/edit?usp=sharing"> https://docs.google.com/document/d/1hWC_WXkM7LTVKbOCcIcA76YJjdG3dom78GVXhPqRWf0/edit?usp=sharing</a> </p>
<p class="note"> Note: Some songs might be missing and some wrong audio files might be present in the playlist.
</div>
</body>
</html>
"""
        message.add_alternative(html_message, subtype='html')
        password = ""
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo()
        server.starttls()
        server.login('', password)
        server.sendmail('', user['email'].lower(), message.as_string())
        server.quit()
        print("Link mailed")
        try:
            os.remove(f"{user['email'].lower()}.zip")
            shutil.rmtree(directory)
        except:
            try:
                os.remove(f"{user['email'].lower()}.zip")
                shutil.rmtree(directory)
            except:
                try:
                    os.remove(f"{user['email'].lower()}.zip")
                    shutil.rmtree(directory)
                except:
                    pass
