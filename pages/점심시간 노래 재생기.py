import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
import time
import socket
import random
import json
import webbrowser

# Load environment variables
load_dotenv()

# Spotify API credentials
SPOTIFY_CLIENT_ID = st.secrets['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = st.secrets['SPOTIFY_CLIENT_SECRET']
SPOTIFY_REDIRECT_URI = st.secrets['SPOTIFY_REDIRECT_URI']

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
if 'playlists' not in st.session_state:
    # Make sure sample tracks have uri field
    st.session_state.playlists = {
        "점심시간 인기곡": [
            {"name": "샘플 곡 1", "id": "sample1", "artists": [{"name": "아티스트 1"}], "uri": "spotify:track:sample1"},
            {"name": "샘플 곡 2", "id": "sample2", "artists": [{"name": "아티스트 2"}], "uri": "spotify:track:sample2"}
        ]
    }
if 'selected_tracks' not in st.session_state:
    st.session_state.selected_tracks = []
if 'user_playlists' not in st.session_state:
    st.session_state.user_playlists = {}
if 'auth_url' not in st.session_state:
    st.session_state.auth_url = None
if 'auth_manager' not in st.session_state:
    st.session_state.auth_manager = None
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False

# Create Spotify auth manager
def create_auth_manager():
    # Use different cache paths to avoid conflicts
    cache_path = f".spotify_cache_{random.randint(1000, 9999)}"
    
    try:
        # Create auth manager
        auth_manager = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope="playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state",
            cache_path=cache_path,
            open_browser=False,
            show_dialog=True  # Force the user to approve every time
        )
        
        st.session_state.auth_manager = auth_manager
        
        # Get authorization URL
        auth_url = auth_manager.get_authorize_url()
        st.session_state.auth_url = auth_url
        
        return auth_manager
    except Exception as e:
        st.error(f"인증 관리자 생성 중 오류: {str(e)}")
        return None

# Initialize Spotify client with proper authentication
def init_spotify():
    current_time = time.time()
    
    # Check if we need a fresh connection or if we're not authenticated
    if (st.session_state.sp is None or 
        current_time - st.session_state.sp_last_refresh > 1800 or
        not st.session_state.is_authenticated):
        
        try:
            if st.session_state.auth_manager and st.session_state.is_authenticated:
                # Use existing auth manager if authenticated
                auth_manager = st.session_state.auth_manager
            else:
                # Otherwise, we can't proceed
                return None
            
            # Create Spotify client
            st.session_state.sp = spotipy.Spotify(auth_manager=auth_manager)
            st.session_state.sp_last_refresh = current_time
            
            # Test the connection
            try:
                # Try to fetch user data to verify the connection
                user_info = st.session_state.sp.current_user()
                if user_info:
                    st.session_state.is_authenticated = True
                    return st.session_state.sp
            except Exception as e:
                st.error(f"Spotify 연결 확인 중 오류: {str(e)}")
                st.session_state.is_authenticated = False
                return None
            
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
            return None
    
    return st.session_state.sp

# Search for tracks
def search_tracks(sp, query):
    try:
        results = sp.search(q=query, type='track', limit=10)
        return results['tracks']['items']
    except Exception as e:
        st.error(f"검색 오류: {str(e)}")
        return []

# Create Spotify player embed
def create_spotify_embed(track_id):
    return f'<iframe src="https://open.spotify.com/embed/track/{track_id}" width="300" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>'

# Check if track has required fields, add defaults if not
def ensure_track_fields(track):
    if not track.get('uri') and track.get('id'):
        track['uri'] = f"spotify:track:{track['id']}"
    return track

# Play next track in queue
def play_next_track():
    if st.session_state.queue:
        next_track = st.session_state.queue[0]  # Get first track without removing
        # Ensure track has uri field
        next_track = ensure_track_fields(next_track)
        st.session_state.current_track = next_track
        try:
            sp = init_spotify()
            if sp and next_track.get('uri'):
                sp.start_playback(uris=[next_track['uri']])
                st.session_state.is_playing = True
                return True
            else:
                st.error(f"곡에 필요한 정보가 없습니다: {next_track.get('name', '제목 없음')}")
                return False
        except Exception as e:
            st.error(f"재생 중 오류 발생: {str(e)}")
            return False
    return False

# Shuffle the queue
def shuffle_queue():
    if len(st.session_state.queue) > 1:
        random.shuffle(st.session_state.queue)
        st.success("대기열이 섞였습니다!")
        return True
    return False

# Skip to next track
def skip_track():
    if len(st.session_state.queue) > 0:
        # Remove current track
        st.session_state.queue.pop(0)
        # Play next track if available
        if st.session_state.queue:
            play_next_track()
            st.success("다음 곡으로 넘어갑니다.")
            return True
        else:
            st.session_state.current_track = None
            st.session_state.is_playing = False
            st.info("더 이상 재생할 곡이 없습니다.")
    return False

# Add tracks to queue
def add_to_queue(tracks):
    if not tracks:
        return False
    
    if isinstance(tracks, list):
        # Ensure all tracks have uri field
        tracks = [ensure_track_fields(track) for track in tracks]
        st.session_state.queue.extend(tracks)
        if len(tracks) == 1:
            st.success(f"{tracks[0]['name']}을(를) 대기열에 추가했습니다!")
        else:
            st.success(f"{len(tracks)}곡을 대기열에 추가했습니다!")
    else:
        # Ensure track has uri field
        track = ensure_track_fields(tracks)
        st.session_state.queue.append(track)
        st.success(f"{track['name']}을(를) 대기열에 추가했습니다!")
    
    # If nothing is playing, start playing the first track
    if not st.session_state.current_track:
        play_next_track()
    
    return True

# Save tracks to playlist
def save_to_playlist(playlist_name, tracks):
    if not tracks:
        return False
    
    if not playlist_name:
        st.error("플레이리스트 이름을 입력해주세요.")
        return False
    
    # Ensure all tracks have required fields
    if isinstance(tracks, list):
        tracks = [ensure_track_fields(track) for track in tracks]
    else:
        tracks = [ensure_track_fields(tracks)]
    
    # Update or create playlist
    if playlist_name in st.session_state.user_playlists:
        # Check for duplicates
        existing_ids = [t.get('id') for t in st.session_state.user_playlists[playlist_name]]
        new_tracks = [t for t in tracks if t.get('id') not in existing_ids]
        if new_tracks:
            st.session_state.user_playlists[playlist_name].extend(new_tracks)
            st.success(f"{len(new_tracks)}곡을 '{playlist_name}' 플레이리스트에 추가했습니다!")
        else:
            st.info("이미 모든 곡이 플레이리스트에 있습니다.")
    else:
        st.session_state.user_playlists[playlist_name] = tracks
        st.success(f"{len(tracks)}곡을 '{playlist_name}' 플레이리스트에 추가했습니다!")
    
    # Save playlists to disk (optional)
    try:
        os.makedirs("playlists", exist_ok=True)
        with open(f"playlists/{playlist_name}.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.user_playlists[playlist_name], f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"플레이리스트 저장 중 오류: {str(e)}")
    
    return True

# Load playlist from saved file (optional)
def load_playlist(playlist_name):
    try:
        with open(f"playlists/{playlist_name}.json", "r", encoding="utf-8") as f:
            playlist = json.load(f)
            st.session_state.user_playlists[playlist_name] = playlist
            return playlist
    except Exception as e:
        st.error(f"플레이리스트 로드 중 오류: {str(e)}")
        return []

# Main app
def main():
    if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI]):
        st.error("Spotify API credentials를 .env 파일에 설정해주세요")
        return

    # Create collapsible section for Spotify login
    with st.expander("Spotify 연결 정보", expanded=not st.session_state.is_authenticated):
        st.write("Spotify 계정으로 로그인하셔야 음악을 재생할 수 있습니다.")
        
        # Show different content based on authentication state
        if not st.session_state.is_authenticated:
            if st.button("Spotify 로그인 시작"):
                # Create new auth manager and get authorization URL
                create_auth_manager()
                st.rerun()
            
            # If we have an auth URL, show it
            if st.session_state.auth_url:
                st.info("아래 링크를 클릭하여 Spotify 계정으로 로그인해주세요.")
                st.markdown(f"[Spotify 로그인 페이지 열기]({st.session_state.auth_url})")
                
                # Open URL automatically option
                if st.button("브라우저에서 자동으로 열기"):
                    try:
                        webbrowser.open(st.session_state.auth_url)
                    except:
                        st.error("브라우저를 열 수 없습니다. 위 링크를 직접 클릭해주세요.")
                
                # Code entry field
                auth_code = st.text_input("로그인 후 리디렉션된 URL 또는 코드를 입력해주세요:")
                if auth_code and st.button("인증 완료"):
                    try:
                        if st.session_state.auth_manager:
                            # Extract code from URL if full URL was pasted
                            if "?" in auth_code and "code=" in auth_code:
                                auth_code = auth_code.split("code=")[1].split("&")[0]
                            
                            # Get access token
                            token_info = st.session_state.auth_manager.get_access_token(auth_code)
                            if token_info:
                                st.session_state.is_authenticated = True
                                sp = init_spotify()
                                if sp:
                                    user = sp.current_user()
                                    st.success(f"성공적으로 로그인되었습니다! 안녕하세요 {user['display_name']}님!")
                                    st.rerun()
                            else:
                                st.error("인증 코드가 올바르지 않습니다.")
                    except Exception as e:
                        st.error(f"인증 중 오류 발생: {str(e)}")
        else:
            # Show connected status
            try:
                sp = init_spotify()
                if sp:
                    user = sp.current_user()
                    st.success(f"Spotify에 연결되었습니다! {user['display_name']}님으로 로그인 중")
                    if st.button("로그아웃"):
                        st.session_state.is_authenticated = False
                        st.session_state.sp = None
                        st.session_state.auth_manager = None
                        st.session_state.auth_url = None
                        st.rerun()
                else:
                    st.warning("연결이 끊겼습니다. 재로그인이 필요합니다.")
                    st.session_state.is_authenticated = False
                    if st.button("다시 로그인"):
                        st.rerun()
            except:
                st.warning("연결 상태를 확인할 수 없습니다. 재로그인이 필요합니다.")
                st.session_state.is_authenticated = False

    # Main content - only show when authenticated
    if st.session_state.is_authenticated and init_spotify():
        try:
            sp = init_spotify()
            
            # Current playing track display
            if st.session_state.current_track:
                st.subheader("현재 재생 중")
                st.write(f"**{st.session_state.current_track['name']}** - {st.session_state.current_track['artists'][0]['name']}")
                st.markdown(create_spotify_embed(st.session_state.current_track['id']), unsafe_allow_html=True)
                
                # Add playback control buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("⏭️ 다음 곡"):
                        skip_track()
                        st.rerun()
                with col2:
                    if st.button("🔀 대기열 섞기"):
                        shuffle_queue()
                        st.rerun()
                with col3:
                    if st.button("🗑️ 대기열 비우기"):
                        st.session_state.queue = []
                        st.success("대기열이 비워졌습니다.")
                        st.rerun()
                
                # Add button to save current track to playlist
                with st.expander("현재 곡을 플레이리스트에 저장"):
                    playlist_name = st.text_input("플레이리스트 이름:", key="save_current_playlist")
                    if st.button("저장", key="save_current_btn"):
                        if playlist_name:
                            save_to_playlist(playlist_name, st.session_state.current_track)
                        else:
                            st.error("플레이리스트 이름을 입력해주세요.")
                
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
                # Show queue as a structured list with selection functionality
                track_names = [f"{i+1}. {track['name']} - {track['artists'][0]['name']}" for i, track in enumerate(st.session_state.queue)]
                
                # Use multiselect for multiple track selection
                selected_indices = []
                selected_tracks = st.multiselect("재생할 곡 선택 (여러 곡 선택 가능)", track_names, format_func=lambda x: x)
                
                # Get indices of selected tracks
                for selected in selected_tracks:
                    for i, track_name in enumerate(track_names):
                        if selected == track_name:
                            selected_indices.append(i)
                
                # Show queue management buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("선택한 곡 삭제") and selected_indices:
                        # Remove tracks in reverse order to avoid index shifting
                        for index in sorted(selected_indices, reverse=True):
                            if index < len(st.session_state.queue):
                                st.session_state.queue.pop(index)
                        st.success("선택한 곡을 대기열에서 삭제했습니다.")
                        st.rerun()
                
                with col2:
                    if st.button("선택한 곡 재생") and selected_indices:
                        # Reorder queue to play selected song first (move it to the beginning)
                        first_selected = min(selected_indices)
                        if first_selected > 0:  # If not already the first song
                            track_to_play = st.session_state.queue.pop(first_selected)
                            st.session_state.queue.insert(0, track_to_play)
                            play_next_track()
                            st.rerun()
                        else:
                            play_next_track()
                            st.rerun()
                
                # Add button to save queue to playlist
                with st.expander("대기열을 플레이리스트로 저장"):
                    queue_playlist_name = st.text_input("플레이리스트 이름:", key="save_queue_playlist")
                    if st.button("대기열 저장", key="save_queue_btn"):
                        if queue_playlist_name:
                            # Get selected tracks from queue or all if none selected
                            tracks_to_save = []
                            if selected_indices:
                                tracks_to_save = [st.session_state.queue[i] for i in selected_indices]
                            else:
                                tracks_to_save = st.session_state.queue
                            
                            save_to_playlist(queue_playlist_name, tracks_to_save)
                        else:
                            st.error("플레이리스트 이름을 입력해주세요.")
            else:
                st.info("대기열이 비어있습니다")
                
                # Suggest some popular tracks when queue is empty
                if st.button("인기 음악 추천 받기"):
                    st.session_state.selected_tracks = st.session_state.playlists["점심시간 인기곡"]
                    add_to_queue(st.session_state.selected_tracks)
                    st.rerun()
            
            # User playlists section
            st.subheader("내 플레이리스트")
            if st.session_state.user_playlists:
                playlist_names = list(st.session_state.user_playlists.keys())
                selected_playlist = st.selectbox("플레이리스트 선택", playlist_names)
                
                if selected_playlist:
                    playlist_tracks = st.session_state.user_playlists[selected_playlist]
                    st.write(f"**{selected_playlist}** - {len(playlist_tracks)}곡")
                    
                    # Show playlist tracks
                    for i, track in enumerate(playlist_tracks):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{i+1}. {track['name']} - {track['artists'][0]['name']}")
                        with col2:
                            if st.button("재생", key=f"play_pl_{i}"):
                                add_to_queue(track)
                                st.rerun()
                    
                    # Add buttons for playlist actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("전체 재생", key="play_all"):
                            add_to_queue(playlist_tracks)
                            st.rerun()
                    with col2:
                        if st.button("섞어서 재생", key="shuffle_play"):
                            shuffled = playlist_tracks.copy()
                            random.shuffle(shuffled)
                            add_to_queue(shuffled)
                            st.rerun()
            else:
                st.info("저장된 플레이리스트가 없습니다.")
                st.write("노래를 검색하고 플레이리스트에 저장해보세요.")
            
            # Search section
            st.subheader("노래 검색")
            search_query = st.text_input("노래 제목 또는 아티스트:")
            if search_query:
                results = search_tracks(sp, search_query)
                
                if results:
                    st.write("검색 결과:")
                    
                    # Create a list of track names for multiselect
                    result_track_names = [f"{track['name']} - {track['artists'][0]['name']}" for track in results]
                    selected_result_indices = []
                    
                    # Use multiselect for track selection
                    selected_results = st.multiselect("대기열에 추가할 곡 선택 (여러 곡 선택 가능)", result_track_names, format_func=lambda x: x)
                    
                    # Get indices of selected tracks from results
                    for selected in selected_results:
                        for i, track_name in enumerate(result_track_names):
                            if selected == track_name:
                                selected_result_indices.append(i)
                    
                    # Show all search results with embeds
                    for i, track in enumerate(results):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{track['name']}** - {track['artists'][0]['name']}")
                            st.markdown(create_spotify_embed(track['id']), unsafe_allow_html=True)
                        with col2:
                            if i in selected_result_indices:
                                st.success("선택됨")
                        with col3:
                            # Add direct playlist save button for each track
                            if st.button("플레이리스트에 저장", key=f"save_track_{i}"):
                                with st.form(key=f"save_form_{i}"):
                                    pl_name = st.text_input("플레이리스트 이름:", key=f"pl_name_{i}")
                                    submitted = st.form_submit_button("저장")
                                    if submitted and pl_name:
                                        save_to_playlist(pl_name, track)
                    
                    # Add button to add selected tracks
                    if st.button("선택한 곡 대기열에 추가") and selected_result_indices:
                        selected_tracks = [results[i] for i in selected_result_indices]
                        add_to_queue(selected_tracks)
                        st.rerun()
                    
                    # Add button to save selected tracks to playlist
                    if selected_result_indices:
                        with st.expander("선택한 곡을 플레이리스트에 저장"):
                            search_playlist_name = st.text_input("플레이리스트 이름:", key="save_search_playlist")
                            if st.button("플레이리스트에 저장", key="save_search_btn"):
                                if search_playlist_name:
                                    tracks_to_save = [results[i] for i in selected_result_indices]
                                    save_to_playlist(search_playlist_name, tracks_to_save)
                                else:
                                    st.error("플레이리스트 이름을 입력해주세요.")
                else:
                    st.write("검색 결과가 없습니다")
            
        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            if "connection" in str(e).lower() or "socket" in str(e).lower():
                st.info("연결 문제로 인해 오류가 발생했습니다. 페이지를 새로고침하고 다시 시도해보세요.")
    elif not st.session_state.is_authenticated:
        st.info("Spotify 로그인이 필요합니다. 상단의 'Spotify 연결 정보'를 클릭하여 로그인해주세요.")
        
    # Add cleanup function - force garbage collection
    import gc
    gc.collect()

if __name__ == "__main__":
    main()