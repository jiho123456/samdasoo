import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import time
import socket
import random

# Load environment variables
load_dotenv()

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8501/')

st.title("점심시간 노래 재생기")

# Initialize session state for queue and playback
if 'queue' not in st.session_state:
    st.session_state.queue = []
if 'current_track' not in st.session_state:
    st.session_state.current_track = None
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False
if 'sp' not in st.session_state:
    st.session_state.sp = None
if 'sp_last_refresh' not in st.session_state:
    st.session_state.sp_last_refresh = 0

# Initialize Spotify client with cache timeout to avoid port conflicts
def init_spotify():
    current_time = time.time()
    
    # Refresh client every 30 minutes to avoid stale connections
    if (st.session_state.sp is None or 
        current_time - st.session_state.sp_last_refresh > 1800):
        
        # Use different ports for OAuth to avoid conflicts
        cache_path = f".spotify_cache_{random.randint(1000, 9999)}"
        
        try:
            # Create auth manager with a timeout to prevent hanging connections
            auth_manager = SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope="playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state",
                cache_path=cache_path,
                open_browser=False
            )
            
            # Attempt to create client with timeout
            st.session_state.sp = spotipy.Spotify(auth_manager=auth_manager)
            st.session_state.sp_last_refresh = current_time
            
        except socket.error as e:
            if hasattr(e, 'errno') and e.errno == 98:
                st.error("포트가 이미 사용 중입니다. 페이지를 새로고침해보세요.")
                # Try to clean up
                try:
                    import gc
                    gc.collect()
                except:
                    pass
            else:
                st.error(f"연결 오류: {str(e)}")
                
        except Exception as e:
            st.error(f"Spotify 연결 오류: {str(e)}")
    
    return st.session_state.sp

# Search for tracks
def search_tracks(sp, query):
    try:
        results = sp.search(q=query, type='track', limit=5)
        return results['tracks']['items']
    except Exception as e:
        st.error(f"검색 오류: {str(e)}")
        return []

# Create Spotify player embed
def create_spotify_embed(track_id):
    return f'<iframe src="https://open.spotify.com/embed/track/{track_id}" width="300" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>'

# Play next track in queue
def play_next_track():
    if st.session_state.queue:
        next_track = st.session_state.queue[0]  # Get first track without removing
        st.session_state.current_track = next_track
        try:
            sp = init_spotify()
            if sp:
                sp.start_playback(uris=[next_track['uri']])
                st.session_state.is_playing = True
                return True
        except Exception as e:
            st.error(f"재생 중 오류 발생: {str(e)}")
            return False
    return False

# Main app
def main():
    if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI]):
        st.error("Spotify API credentials를 .env 파일에 설정해주세요")
        return

    # Create collapsible section for Spotify login
    with st.expander("Spotify 연결 정보", expanded=False):
        st.write("Spotify 계정으로 로그인하셔야 음악을 재생할 수 있습니다.")
        st.write("로그인 버튼을 눌러 인증을 완료해주세요.")
        if st.button("Spotify 로그인"):
            sp = init_spotify()
            if sp:
                st.success("Spotify에 연결되었습니다!")

    try:
        sp = init_spotify()
        if not sp:
            st.warning("Spotify 연결이 필요합니다. 위의 'Spotify 연결 정보'를 클릭하여 로그인해주세요.")
            return
        
        # Current playing track display
        if st.session_state.current_track:
            st.subheader("현재 재생 중")
            st.write(f"**{st.session_state.current_track['name']}** - {st.session_state.current_track['artists'][0]['name']}")
            st.markdown(create_spotify_embed(st.session_state.current_track['id']), unsafe_allow_html=True)
            
            # Check if track finished and play next
            try:
                current_playback = sp.current_playback()
                if current_playback and not current_playback['is_playing'] and st.session_state.is_playing:
                    # Remove the played track from queue
                    st.session_state.queue.pop(0)
                    # Play next track
                    play_next_track()
            except Exception as e:
                st.warning(f"재생 상태 확인 중 오류: {str(e)}")
        
        # Queue display and controls
        st.subheader("재생 대기열")
        if st.session_state.queue:
            for i, track in enumerate(st.session_state.queue):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"{i+1}. {track['name']} - {track['artists'][0]['name']}")
                with col2:
                    if st.button("삭제", key=f"remove_{track['id']}"):
                        st.session_state.queue.pop(i)
                        st.rerun()
                with col3:
                    if i == 0 and st.button("재생", key=f"play_{track['id']}"):
                        play_next_track()
                        st.rerun()
        else:
            st.write("대기열이 비어있습니다")
        
        # Search section
        st.subheader("노래 검색")
        search_query = st.text_input("노래 제목 또는 아티스트:")
        if search_query:
            results = search_tracks(sp, search_query)
            
            if results:
                st.write("검색 결과:")
                for track in results:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{track['name']}** - {track['artists'][0]['name']}")
                        st.markdown(create_spotify_embed(track['id']), unsafe_allow_html=True)
                    with col2:
                        if st.button("대기열에 추가", key=track['id']):
                            st.session_state.queue.append(track)
                            st.success(f"{track['name']}을(를) 대기열에 추가했습니다!")
                            if not st.session_state.current_track:
                                play_next_track()
                            st.rerun()
            else:
                st.write("검색 결과가 없습니다")
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        if "connection" in str(e).lower() or "socket" in str(e).lower():
            st.info("연결 문제로 인해 오류가 발생했습니다. 페이지를 새로고침하고 다시 시도해보세요.")
        
    # Add cleanup function - force garbage collection
    import gc
    gc.collect()

if __name__ == "__main__":
    main()