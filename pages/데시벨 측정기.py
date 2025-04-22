import streamlit as st
import sounddevice as sd
import numpy as np
import time

st.title("데시벨 측정기")

# Constants
SAMPLE_RATE = 44100
DURATION = 1.0  # seconds
REFERENCE_PRESSURE = 20e-6  # 20 microPascals (standard reference pressure)

def calculate_db(samples):
    # Calculate RMS (Root Mean Square) of the audio samples
    rms = np.sqrt(np.mean(samples**2))
    # Convert to decibels
    if rms > 0:
        db = 20 * np.log10(rms / REFERENCE_PRESSURE)
        return max(0, db)  # Ensure we don't return negative values
    return 0

def measure_sound():
    # Record audio
    recording = sd.rec(int(SAMPLE_RATE * DURATION), samplerate=SAMPLE_RATE, channels=1)
    sd.wait()  # Wait until recording is finished
    return recording

# Create a placeholder for the decibel display
db_display = st.empty()

# Main measurement loop
while True:
    # Record and calculate decibels
    audio_data = measure_sound()
    db_level = calculate_db(audio_data)
    
    # Display the decibel level
    db_display.text(f"{db_level:.1f}만큼의 소리에요")
    
    # Add a small delay to prevent excessive CPU usage
    time.sleep(0.1)



