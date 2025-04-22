import streamlit as st
import numpy as np

st.title("데시벨 측정기")

# HTML and JavaScript for audio capture
audio_html = """
<script>
    const constraints = {
        audio: true,
        video: false
    };
    
    let audioContext;
    let analyser;
    let microphone;
    let javascriptNode;
    let lastDbLevel = 0;
    
    function startAudio() {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 2048;
        
        navigator.mediaDevices.getUserMedia(constraints)
            .then(function(stream) {
                microphone = audioContext.createMediaStreamSource(stream);
                microphone.connect(analyser);
                
                javascriptNode = audioContext.createScriptProcessor(2048, 1, 1);
                analyser.connect(javascriptNode);
                javascriptNode.connect(audioContext.destination);
                
                javascriptNode.onaudioprocess = function() {
                    const array = new Uint8Array(analyser.frequencyBinCount);
                    analyser.getByteFrequencyData(array);
                    const average = array.reduce((a, b) => a + b) / array.length;
                    const db = 20 * Math.log10(average / 255);
                    
                    // Only update if the change is significant
                    if (Math.abs(db - lastDbLevel) > 1) {
                        lastDbLevel = db;
                        window.parent.postMessage({type: 'db_level', value: db}, '*');
                    }
                };
            })
            .catch(function(err) {
                console.error('Error accessing microphone:', err);
                window.parent.postMessage({type: 'error', value: err.message}, '*');
            });
    }
    
    startAudio();
</script>
"""

# Display the audio capture interface
st.components.v1.html(audio_html, height=0)

# Create a placeholder for the decibel display
db_display = st.empty()

# Initialize session state for db level
if 'db_level' not in st.session_state:
    st.session_state.db_level = 0

# Function to calculate decibels
def calculate_db(level):
    # Convert the level to a reasonable decibel range
    # The raw level from the audio API is between -Infinity and 0
    # We'll map it to a more readable range (0-100)
    if level <= -100:
        return 0
    return abs(level)

# Function to get sound description
def get_sound_description(db_level):
    if db_level < 20:
        return "🔇 귀를 기울여야 들릴 정도의 소리 (나뭇잎 부딪히는 소리)"
    elif db_level < 30:
        return "🔈 아주 조용한 소리 (속삭이는 소리)"
    elif db_level < 40:
        return "🔉 조용한 소리 (도서관 내 소음)"
    elif db_level < 50:
        return "🔊 보통 소리 (일반적인 대화)"
    elif db_level < 60:
        return "🔊 약간 큰 소리 (시끄러운 레스토랑)"
    elif db_level < 70:
        return "🔊 큰 소리 (전화벨 소리)"
    elif db_level < 80:
        return "🔊 매우 큰 소리 (시끄러운 거리)"
    elif db_level < 90:
        return "🔊 귀가 아픈 소리 (전동 공구 소음)"
    elif db_level < 100:
        return "🔊 귀가 아프고 위험한 소리 (비행기 이륙 소음)"
    else:
        return "🔊 귀에 심각한 손상을 줄 수 있는 소리 (제트기 엔진 소음)"

# Create a container for the visualization
viz_container = st.empty()

# Main display loop
while True:
    try:
        # Get the latest db level from session state
        db_level = st.session_state.db_level
        
        # Display the decibel level with a visual indicator
        with db_display.container():
            st.markdown(f"""
                <div style="text-align: center;">
                    <h2>{db_level:.1f} dB</h2>
                    <div style="width: 100%; height: 20px; background: linear-gradient(to right, 
                        #4CAF50 0%, 
                        #FFC107 {min(db_level, 50)}%, 
                        #F44336 {min(db_level, 100)}%); 
                        border-radius: 10px;">
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Display the sound description
            description = get_sound_description(db_level)
            if db_level < 60:
                st.success(description)
            elif db_level < 80:
                st.warning(description)
            else:
                st.error(description)
        
        # Add a small delay to prevent excessive CPU usage
        st.rerun()
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        break



