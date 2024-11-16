import subprocess
import os
import argparse
from pydub import AudioSegment, silence

def extract_audio(input_video, temp_audio):
    # Wyodrębnienie audio z wideo
    command = ["ffmpeg", "-i", input_video, "-q:a", "0", "-map", "a", temp_audio]
    subprocess.run(command, check=True)
    print(f"Audio wyodrębnione do: {temp_audio}")

def remove_silence(temp_audio, cleaned_audio, silence_duration=1.5, silence_threshold="-40dB", silence_padding=1.0):
    # Usuwanie ciszy z audio przy pomocy FFmpeg, z wstawieniem ciszy 1s w miejsce wyciętych fragmentów
    command = [
        "ffmpeg", "-i", temp_audio, 
        "-af", f"silenceremove=start_periods=1:start_silence={silence_duration}:start_threshold={silence_threshold}:detection=peak,aresample=async=1",
        "-y", cleaned_audio
    ]
    subprocess.run(command, check=True)
    
    # Dodanie ciszy o długości silence_padding w miejsce wyciętych fragmentów
    audio = AudioSegment.from_file(cleaned_audio)
    silence_segment = AudioSegment.silent(duration=silence_padding * 1000)  # 1-sekundowy fragment ciszy

    result_audio = AudioSegment.empty()
    start = 0
    # Przetwórz i wstaw ciszę w miejsca wyciętych fragmentów
    silent_segments = silence.detect_silence(audio, min_silence_len=silence_duration * 1000, silence_thresh=-40)

    for start_time, end_time in silent_segments:
        result_audio += audio[start:start_time]  # Dodaj audio przed ciszą
        result_audio += silence_segment  # Dodaj 1 sekundę ciszy
        start = end_time

    result_audio += audio[start:]  # Dodaj pozostałą część audio
    result_audio.export(cleaned_audio, format="wav")  # Zapisz przetworzone audio z ciszą

    print(f"Cisza usunięta, nowe audio zapisane jako: {cleaned_audio}")

def combine_audio_video(input_video, cleaned_audio, output_video):
    # Połączenie wideo z przetworzonym audio
    command = [
        "ffmpeg", "-i", input_video, "-i", cleaned_audio, 
        "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", "-shortest", output_video
    ]
    subprocess.run(command, check=True)
    print(f"Gotowy plik wideo zapisany jako: {output_video}")

def main():
    parser = argparse.ArgumentParser(description="Remove silence from video and add silence padding.")
    parser.add_argument("input_video", help="Path to the input video file")
    parser.add_argument("output_video", help="Path to the output video file")
    args = parser.parse_args()

    # Nazwy plików tymczasowych
    temp_audio = "temp_audio.wav"
    cleaned_audio = "temp_audio_cleaned.wav"
    
    try:
        # 1. Wyodrębnij audio
        extract_audio(args.input_video, temp_audio)
        
        # 2. Usuń ciszę z audio
        remove_silence(temp_audio, cleaned_audio, silence_duration=1.5, silence_padding=1.0)
        
        # 3. Połącz przetworzone audio z oryginalnym wideo
        combine_audio_video(args.input_video, cleaned_audio, args.output_video)
    
    finally:
        # Usunięcie plików tymczasowych
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        if os.path.exists(cleaned_audio):
            os.remove(cleaned_audio)
        print("Pliki tymczasowe usunięte.")

if __name__ == "__main__":
    main()