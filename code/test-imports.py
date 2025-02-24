import sys
import traceback
print("Start programu")

try:
    print("Importing moviepy...")
    from moviepy.editor import VideoFileClip
    print("moviepy OK")

    print("Importing librosa...")
    import librosa
    print("librosa OK")

    print("Importing scipy.io.wavfile...")
    from scipy.io import wavfile
    print("scipy.io.wavfile OK")

    print("Importing numpy...")
    import numpy as np
    print("numpy OK")
except Exception as e:
    print(f"Błąd importu: {str(e)}")
    traceback.print_exc()

print("Koniec programu")