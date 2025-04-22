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
                    window.parent.postMessage({type: 'db_level', value: db}, '*');
                };
            })
            .catch(function(err) {
                console.error('Error accessing microphone:', err);
            });
    }
    
    startAudio();
</script>
"""

# Display the audio capture interface
st.components.v1.html(audio_html, height=0)

# Create a placeholder for the decibel display
db_display = st.empty()

# Function to calculate decibels
def calculate_db(level):
    # Convert the level to a reasonable decibel range
    # The raw level from the audio API is between -Infinity and 0
    # We'll map it to a more readable range (0-100)
    if level <= -100:
        return 0
    return abs(level)

# Main loop
while True:
    # The actual decibel level will be updated by the JavaScript
    # For now, we'll show a placeholder
    db_display.text("마이크 접근 권한을 허용해주세요...")
    
    # Add a small delay to prevent excessive CPU usage
    st.rerun()



