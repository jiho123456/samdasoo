import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

st.title("점심시간 노래 재생기")

# Initialize Spotify client
def init_spotify():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope="playlist-modify-public playlist-modify-private"
    ))

# Search for tracks
def search_tracks(sp, query):
    results = sp.search(q=query, type='track', limit=5)
    return results['tracks']['items']

# Add tracks to playlist
def add_to_playlist(sp, playlist_id, track_uris):
    sp.playlist_add_items(playlist_id, track_uris)

# Create Spotify player embed
def create_spotify_embed(track_id):
    return f'<iframe src="https://open.spotify.com/embed/track/{track_id}" width="300" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>'

# Main app
def main():
    if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI]):
        st.error("Please set up your Spotify API credentials in the .env file")
        return

    try:
        sp = init_spotify()
        
        # Search for songs
        search_query = st.text_input("노래 검색:")
        if search_query:
            results = search_tracks(sp, search_query)
            
            if results:
                st.write("검색 결과:")
                for track in results:
                    # Create a container for each track
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            # Display track info
                            st.write(f"**{track['name']}** - {track['artists'][0]['name']}")
                            # Add Spotify player embed
                            st.markdown(create_spotify_embed(track['id']), unsafe_allow_html=True)
                        with col2:
                            if st.button("플레이리스트에 추가", key=track['id']):
                                # Get or create playlist
                                playlists = sp.current_user_playlists()
                                if not playlists['items']:
                                    playlist = sp.user_playlist_create(
                                        sp.current_user()['id'],
                                        "점심시간 플레이리스트",
                                        public=True
                                    )
                                else:
                                    playlist = playlists['items'][0]
                                
                                # Add track to playlist
                                add_to_playlist(sp, playlist['id'], [track['uri']])
                                st.success(f"{track['name']}을(를) {playlist['name']}에 추가했습니다!")
            else:
                st.write("검색 결과가 없습니다")
                
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()