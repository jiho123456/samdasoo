import streamlit as st
import numpy as np

st.title("데시벨 측정기")

# HTML and JavaScript for audio capture
audio_html = """
<div id="audio-container"></div>
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
                    let db = 20 * Math.log10(average / 255);
                    
                    // FIX 1: Set minimum decibel value to -1
                    db = Math.max(db, -1);
                    
                    // FIX 2: Add 100 to the decibel value to avoid negative numbers
                    const displayDb = db + 100;
                    
                    // Only update if the change is significant
                    if (Math.abs(db - lastDbLevel) > 1) {
                        lastDbLevel = db;
                        // Update the display
                        document.getElementById('audio-container').innerHTML = `
                            <div style="text-align: center;">
                                <h2>${displayDb.toFixed(1)} dB</h2>
                                <div style="width: 100%; height: 20px; background: linear-gradient(to right, 
                                    #4CAF50 0%, 
                                    #FFC107 ${Math.min(displayDb/2, 50)}%, 
                                    #F44336 ${Math.min(displayDb/2, 100)}%); 
                                    border-radius: 10px;">
                                </div>
                                <p style="font-size: 12px; color: gray;">실제 dB: ${db.toFixed(1)} (보정값: +100)</p>
                            </div>
                        `;
                        
                        // Send the real dB value to Streamlit
                        if (window.parent && window.parent.Streamlit) {
                            const dbValues = {
                                "real_db": db,
                                "display_db": displayDb
                            };
                            window.parent.Streamlit.setComponentValue(JSON.stringify(dbValues));
                        }
                    }
                };
            })
            .catch(function(err) {
                console.error('Error accessing microphone:', err);
                document.getElementById('audio-container').innerHTML = `
                    <div style="text-align: center; color: red;">
                        마이크 접근 권한을 허용해주세요...
                    </div>
                `;
            });
    }
    
    startAudio();
</script>
"""

# Display the audio capture interface with component state
component_value = st.components.v1.html(audio_html, height=150, key="db_meter")

# Extract values from component if available
current_db = -1
display_db = 99  # Default values
if component_value:
    try:
        import json
        values = json.loads(component_value)
        current_db = values.get("real_db", -1)
        display_db = values.get("display_db", 99)
    except:
        pass

# Function to get sound description
def get_sound_description(db_level):
    # Use the real dB level (before +100 adjustment) for descriptions
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

# Display additional information
st.subheader("소리 정보")
st.write(f"현재 소리 수준: **{display_db:.1f} dB** (보정값: +100)")
st.write(f"실제 소리 수준: **{current_db:.1f} dB**")
st.write(get_sound_description(current_db))

# Add explanation about the +100 adjustment
st.info("""
**참고:** 이 측정기는 음향 측정값에 +100을 더한 값을 표시합니다. 실제 데시벨 값은 표시된 값에서 100을 뺀 값입니다.
또한 웹 마이크로 측정한 값이므로 정확한 측정을 위해서는 전문 장비가 필요합니다.
""")

# Add auto-refresh with longer interval to reduce flickering
st_autorefresh = st.empty()
st_autorefresh.code("소음 측정 중...", language=None)



