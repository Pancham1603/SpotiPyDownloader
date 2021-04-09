from flask import Flask, render_template, request, session, redirect, send_file, flash
import base64
import requests
import datetime
from urllib.parse import urlencode
import os
import pymongo
import re
from youtube_search import YoutubeSearch
from pytube import extract
from pytube import YouTube
from math import ceil

client_id = '***REMOVED***'
client_secret = '***REMOVED***'

client = pymongo.MongoClient(
    "***REMOVED***")
db = ***REMOVED***
collection1 = ***REMOVED***
collection2 = ***REMOVED***
collection3 = ***REMOVED***
collection4 = ***REMOVED***
collection5 = ***REMOVED***
collection6 = db['individual_song_stats']


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

    def search(self, query, search_type='track'):
        access_token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        endpoint = 'https://api.spotify.com/v1/search'
        data = urlencode({
            'q': query,
            'type': search_type.lower()
        })
        lookup_url = f"{endpoint}?{data}"
        r = requests.get(lookup_url, headers=headers)
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


class MyYouTube(YouTube):
    # https://github.com/nficano/pytube/blob/master/pytube/__main__.py#L150
    def prefetch(self):
        """Eagerly download all necessary data.

        Eagerly executes all necessary network requests so all other
        operations don't does need to make calls outside of the interpreter
        which blocks for long periods of time.

        :rtype: None

        """
        self.watch_html = request.get(url=self.watch_url)
        self.embed_html = request.get(url=self.embed_url)
        self.age_restricted = extract.is_age_restricted(self.watch_html)
        self.vid_info_url = extract.video_info_url(
            video_id=self.video_id,
            watch_url=self.watch_url,
            watch_html=self.watch_html,
            embed_html=self.embed_html,
            age_restricted=self.age_restricted,
        )
        self.vid_info = request.get(self.vid_info_url)
        if not self.age_restricted:
            self.js_url = extract.js_url(self.watch_html, self.age_restricted)
            self.js = request.get(self.js_url)


app = Flask(__name__)
app.secret_key = 'demo'
spotify = SpotifyAPI(client_id, client_secret)


@app.route('/home')
@app.route('/')
def initiation():
    stats = collection3.find()
    for stat in stats:
        user_count = stat['users']
        song_count = stat['songs']
        playlist_count = stat['playlists']
    # flash(f'{int(user_count)}', 'user-count')
    # flash(f'{int(playlist_count)}', 'playlist-count')
    # flash(f'{int(song_count)}', 'song-count')
    try:
        results = collection5.find()
        for result in results:
            try:
                path = result['path']
                collection5.delete_one(
                    {
                        'path': path
                    }
                )
                os.remove(path)
            except:
                collection5.delete_one(
                    {
                        'path': path
                    }
                )
    except:
        pass
    return render_template("index.html")


@app.route('/queuedownload', methods=['GET', 'POST'])
def queueDownload():
    user_data = request.form
    session['name'] = user_data['name']
    session['email'] = user_data['email'].lower()
    session['link'] = user_data['link']
    session['num'] = user_data['num']
    results = collection1.find({'email': session['email'].lower()})
    data = spotify.playlist(link=session['link'], num=20)
    songs = []
    for item in range(20):
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
                    'email': session['email'].lower(),
                    'link': session['link'],
                    'length_req': session['num'],
                }
            )
            flash(f"""Download queued! You'll receive a download link on your e-mail by midnight.""", 'success')
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

            query = {'email': session['email'].lower()}
            collection1.update_one(query, document)
            collection2.insert_one(
                {
                    'name': session['name'],
                    'email': session['email'].lower(),
                    'link': session['link'],
                    'length_req': session['num']
                }
            )
            flash(f"""Download queued! You'll receive a download link on your e-mail by midnight.""", 'success')
            return redirect('/')
    else:
        flash("Enter a valid Spotify Playlist URL!", 'error')
        return redirect('/')


@app.route("/fetchsearchresults", methods=['GET', 'POST'])
def fetchsearchresults():
    spotify = SpotifyAPI(client_id, client_secret)
    response = request.form
    query = response['query']
    name = response['name']
    email = response['email']
    # For entry in user database
    results = collection1.find({'email': email.lower()})
    if results.count() == 0:
        collection1.insert_one({
            'name': name,
            'email': email.lower(),
            'request': {
                'search_query': query,
                'time': datetime.datetime.now()
            },
            'uses': 1
        })
    elif results.count() != 0:
        for result in results:
            use = result['uses'] + 1

        document = {'$set':
            {f'request{use}': {
                'search_query': query,
                'time': datetime.datetime.now()
            },
                'uses': use}
        }

        db_query = {'email': email.lower()}
        collection1.update_one(db_query, document)
    # fetching matches from spotify
    results = spotify.search(query)
    result_length = len(results['tracks']['items'])
    if result_length == 0:
        flash(f"No matches found!\nfor '{query}'", 'error')
        search_results = []
        length = 0
        return render_template("search_results.html", search_results=search_results, length=length)
    else:
        unsorted_search_results = []
        popularity_index = []
        count = 0
        for result in range(result_length):
            song = results['tracks']['items'][result]['album']['name']
            artist = results['tracks']['items'][result]['album']['artists'][0]['name']
            popularity = results['tracks']['items'][result]['popularity']
            img = results['tracks']['items'][result]['album']['images'][1]['url']
            re_string = f"/{song}{artist.title()}"
            redirect = re.sub('[^A-Za-z0-9]+', '', re_string.lower())
            popularity_index.append(popularity)
            unsorted_search_results.append({
                'name': f"{song} - {artist.title()}",
                'redirect': f"/download/{redirect}",
                'popularity': int(popularity),
                'img_src': img}
            )
            count += 1
            collection4.insert_one(
                {
                    'name': f"{song} - {artist.title()}",
                    'redirect': redirect,
                    'img_src': img
                }
            )

        search_results = []
        for x in popularity_index:
            max_index = popularity_index.index(max(popularity_index))
            search_results.insert(-1, unsorted_search_results[max_index])
            popularity_index.pop(max_index)
            unsorted_search_results.pop(max_index)
        top_song = search_results.pop()
        search_results.insert(0, top_song)
        length = len(search_results)
        half = int(ceil(length / 2))
        flash(f"""Click on the required song.""", 'success')
        return render_template("search_results.html", search_results=search_results, length=length, half=half)


@app.route('/download/<path:songname>')
def custom_song_path(songname):
    indi_uses = collection6.find()
    for uses in indi_uses:
        use = uses['songs']
    new_use = use + 1
    new_doc = {
        '$set': {
            'songs': new_use,
        }
    }
    query = {
        'songs': use
    }
    collection6.update_one(query, new_doc)

    results = collection4.find_one(
        {
            'redirect': songname
        }
    )
    song = results['name']
    img = results['img_src']
    base = 'https://www.youtube.com'
    try:
        print(f"Downloading: {song}")
        result = YoutubeSearch(song, max_results=1).to_dict()
        suffix = result[0]['url_suffix']
        link = base + suffix
        out_file = MyYouTube(link).streams.filter(only_audio=True).first().download()
        base, ext = os.path.splitext(out_file)
        new_file = base + '.mp3'
        os.rename(out_file, new_file)
        collection5.insert_one(
            {
                'path': new_file
            }
        )
        return send_file(new_file, mimetype='audio/mpeg', as_attachment=True, attachment_filename=f"{song}.mp3")
    except:
        try:
            print(f"Downloading: {song}")
            result = YoutubeSearch(song, max_results=1).to_dict()
            suffix = result[0]['url_suffix']
            link = base + suffix
            out_file = MyYouTube(link).streams.filter(only_audio=True).first().download()
            base, ext = os.path.splitext(out_file)
            new_file = base + '.mp3'
            os.rename(out_file, new_file)
            collection5.insert_one(
                {
                    'path': new_file
                }
            )
            return send_file(new_file, mimetype='audio/mpeg', as_attachment=True, attachment_filename=f"{song}.mp3")
        except:
            return render_template('error500.html')


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
