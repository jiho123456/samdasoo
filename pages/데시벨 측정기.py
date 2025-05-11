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

# Simple display with no extra parameters - using a different method
st.markdown(f'<div style="height:150px">{audio_html}</div>', unsafe_allow_html=True)

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
st.write("데시벨 측정기는 마이크를 통해 소리를 측정하여 보여줍니다.")
st.write("위 측정기에서 측정값을 확인하세요.")

# Add explanation about the +100 adjustment
st.info("""
**참고:** 이 측정기는 음향 측정값에 +100을 더한 값을 표시합니다. 실제 데시벨 값은 표시된 값에서 100을 뺀 값입니다.
또한 웹 마이크로 측정한 값이므로 정확한 측정을 위해서는 전문 장비가 필요합니다.
""")

# Add sound level reference
st.subheader("소리 수준 참고")
reference_data = {
    "소리 유형": ["나뭇잎 부딪히는 소리", "속삭이는 소리", "도서관 내 소음", "일반적인 대화", 
                "시끄러운 레스토랑", "전화벨 소리", "시끄러운 거리", "전동 공구 소음", 
                "비행기 이륙 소음", "제트기 엔진 소음"],
    "실제 dB": ["0-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-90", "90-100", "100+"],
    "보정 dB": ["100-120", "120-130", "130-140", "140-150", "150-160", "160-170", "170-180", "180-190", "190-200", "200+"]
}
st.table(reference_data)

# Remove auto-refresh to avoid potential issues
# st_autorefresh = st.empty()
# st_autorefresh.code("소음 측정 중...", language=None)



