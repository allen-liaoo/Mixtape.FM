import db
import json
from os import environ as env
from dotenv import find_dotenv, load_dotenv
from urllib.parse import quote_plus, urlencode
from flask import Flask, request, render_template, redirect, session, Response, jsonify
from spotify import get_playlist_info

import auth, db, spotify

def create_app():
  app = Flask(__name__)
  app.register_blueprint(auth.app)

  # load flask secret key
  ENV_FILE = find_dotenv()
  if ENV_FILE:
    load_dotenv(ENV_FILE)
  app.secret_key = env.get("FLASK_SECRET")

  # setup other modules
  with app.app_context():
    db.setup()
    auth.setup()
  return app

app = create_app()
@app.route("/")
@app.route('/home', methods=['GET'])
@app.route('/homepage', methods=['GET'])
def homepage():
    #print(db.get_top_playlists()) 
    return render_template('homepage.html.jinja', user_session=session.get('user'), pretty=json.dumps(session.get('user'), indent=4),
    playlists = [{'image':'image goes here','name':'playlist name goes here','rating':'rating goes here','tags':['tag1','tag2','tag3']}])

@app.route('/spotify/login', methods=['GET'])
@auth.require_login
def spotify_login():
  scope = 'user-top-read'
  # Query string is used to retrieve information from a database
  return redirect('https://accounts.spotify.com/authorize?' +
      urlencode({
        "response_type": 'code',
        "client_id": env['SPOTIFY_CLIENT_ID'],
        "scope": scope,
        "redirect_uri": spotify.spotify_redirect_uri
    },
    quote_via=quote_plus))

@app.route('/spotify/callback', methods=['GET'])
@auth.require_login(redirect_to="/spotify/login")
def spotify_callback():
  code = request.args.get('code')
  session["spotify"] = spotify.connect_spotify(session['user_id'], code)
  playlist_json = get_playlist_info(session["spotify"].get("access_token"))
  info = []
  playlist_ids = []
  for playlist_info in playlist_json.get('items'):
    info.append({'image': playlist_info.get('images')[0].get('url'), 'name': playlist_info.get('name'), 'rating': 0})
    playlist_ids.append(playlist_info.get('id'))

  db_playlists = db.getPlaylists(session['user_id'])
  db_playlist_names = [playlist.get('name') for playlist in db_playlists]
  print(db_playlist_names)

  for playlist in info:
    # Makes it so the database won't add a duplicate playlist
    if playlist.get('name') not in db_playlist_names:
        db.insert_playlist(session['user_id'], playlist.get('name'))

#   for playlist_id in playlist_ids:
#     spotify.get_songs_from_playlist(session["spotify"].get("access_token"), playlist_id)
#   playlist = [{'image': 'https://mosaic.scdn.co/640/ab67616d0000b2732887f8c05b5a9f1cb105be29ab67616d0000b273c4e6adea69105e6b6e214b96ab67616d0000b273d81a092eb373ded457d94eecab67616d0000b273e6d6d392a66a7f9172fe57c8',
#               'name': 'Nebraska',
#               'rating': 0}]
  return render_template('homepage.html.jinja', playlists=info)

# Call this route like:.../spotify/search?q=baby%20shark
# The string after "?q=" must be url encoded
# Return a json object where the list of tracks is in the "items" property
# See: https://developer.spotify.com/documentation/web-api/reference/search
@app.route('/spotify/search', methods=['GET'])
@auth.require_login
def spotify_search():
    if session.get('spotify') is None:
       return Response("Need to be logged in to Spotify to use this feature!", status=400, mimetype='text/plain')

    spotify.refresh_spotify_tokens(session['user_id'], session['spotify'])

    search_string = request.args.get('q')
    if (search_string is None): 
       return Response("Need to pass in a query string!", status=400, mimetype='text/plain')

    search_res = spotify.search_song(session['spotify']['access_token'], search_string)  # flask jsonifies this
    return jsonify(search_res)

@app.route('/search', methods=['POST','GET'])
def search():
    searchtext = request.form.get("SerchBar")
    #print(db.search(searchtext))
    return render_template('search.html.jinja',user_session = session.get('user'), playlists = [{'image':'image goes here','name':'playlist name goes here','rating':'rating goes here','tags':['tag1','tag2','tag3']}])
@app.route('/playlist/<int:p_id>', methods=['POST','GET'])
def playlist(p_id):
    return render_template('playlist.html.jinja', playlist_id=p_id,user_session = session.get('user'), user_id=session.get('user_id'), songs= ["Minnesota March","Minnesota Rouser"],comments= ["Lovely","good vibes"])
@app.route('/settings', methods=['GET'])
@auth.require_login
def settings():
    return render_template('settings.html.jinja', user_id=session.get('user_id'),settings = 
  {"Import Spotify playlists":["button",["/spotify/login","get",session.get('spotify')]]})

@app.route('/library', methods=['POST','GET'])
@auth.require_login
def library():
    print(session.get('user'))
    #print(db.get_user_playlists(0))
    return render_template('user_library.html.jinja', user_session=session.get('user'), user_id=session.get('user_id'))

@app.route('/edit-playlist/<int:p_id>', methods=['POST','GET'])
@app.route('/edit-playlist', methods=['POST','GET'])  # Incase user is making a completey new playlist
@auth.require_login
def editplaylist(p_id=None):
    print(p_id)
    if p_id is None:  # New playlist
        return render_template('create_edit_playlist.html.jinja', playlist_id=p_id, user_session=session.get('user'),playlistDetails= [],songs=[],user_id=session.get('user_id'))
    
    playlist_details = [{'playlistID': "someID", 'playlistPicture': "someImg", 'playlistName': "myPlaylist1"}]
    songs = [{'songID': "", 'songName': "mySong1", 'songImage': ""}]
    return render_template('create_edit_playlist.html.jinja', playlist_id=p_id, user_session=session.get('user'),playlistDetails=playlist_details, songs=songs, user_id=session.get('user_id'))

# @app.route('/rate-playlist', methods=['POST'])
def ratePlaylist():
    user_id = request.args.get('user_id')
    playlist_id = request.args.get('playlist_id')
    stars = request.args.get('stars')
    comment = request.args.get('comment')
    if (db.get_comment(user_id, playlist_id) != []):
        print("User has already left comment for playlist with id: " + str(playlist_id))
    else:
        db.insertNewComment(user_id, playlist_id, stars, comment)


