import os
import sys
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
import librosa
import soundfile as sf
import numpy as np
import logging


# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Wymuszone wyświetlanie logów
logger = logging.getLogger('')
logger.setLevel(logging.INFO)

def reduce_echo(input_audio, output_audio, threshold=0.3, frame_length=2048, hop_length=512):
    """
    Funkcja usuwająca pogłosy z pliku audio.
    """
    try:
        logger.info(f"Wczytywanie pliku audio: {input_audio}")
        y, sr = librosa.load(input_audio, sr=None)

        logger.info("Obliczanie STFT...")
        S = librosa.stft(y, n_fft=frame_length, hop_length=hop_length)
        magnitude, phase = np.abs(S), np.angle(S)

        logger.debug(f"Średnia energia: {np.mean(magnitude)}")
        avg_energy = np.mean(magnitude, axis=1, keepdims=True)
        mask = magnitude > threshold * avg_energy
        magnitude_cleaned = magnitude * mask

        logger.info("Rekonstrukcja audio po redukcji pogłosu...")
        S_cleaned = magnitude_cleaned * np.exp(1j * phase)
        y_cleaned = librosa.istft(S_cleaned, hop_length=hop_length)

        logger.info(f"Zapisywanie przetworzonego audio: {output_audio}")
        sf.write(output_audio, y_cleaned, sr)
    except Exception as e:
        logger.error(f"Błąd w trakcie usuwania pogłosów: {str(e)}")
        raise e

def process_video(input_video, output_video, temp_audio="temp_audio.wav", cleaned_audio="cleaned_audio.wav"):
    """
    Główna funkcja przetwarzająca wideo z usuwaniem pogłosów z audio.
    """
    try:
        # Dodaj print dla debugowania
        print(f"Sprawdzam plik: {input_video}")
        
        if not os.path.exists(input_video):
            print(f"BŁĄD: Plik {input_video} nie istnieje!")
            sys.exit(1)

        logger.info("Wczytywanie pliku wideo...")
        video = VideoFileClip(input_video)

        logger.info("Wyodrębnianie audio z wideo...")
        audio = video.audio
        logger.info(f"Zapisywanie audio do pliku tymczasowego: {temp_audio}")
        audio.write_audiofile(temp_audio)

        logger.info("Rozpoczynanie procesu redukcji pogłosu...")
        reduce_echo(temp_audio, cleaned_audio)

        logger.info("Łączenie przetworzonego audio z wideo...")
        new_audio = AudioFileClip(cleaned_audio)
        final_video = video.set_audio(new_audio)
        logger.info(f"Zapisywanie finalnego wideo do: {output_video}")
        final_video.write_videofile(output_video, codec="libx264", audio_codec="aac")

        # Czyszczenie plików tymczasowych
        logger.info(f"Usuwanie plików tymczasowych: {temp_audio}, {cleaned_audio}")
        os.remove(temp_audio)
        os.remove(cleaned_audio)
        logger.info("Proces zakończony pomyślnie.")
    except Exception as e:
        print(f"Wystąpił błąd: {str(e)}")
        sys.exit(1)
        raise e
    finally:
        # Czyszczenie plików tymczasowych
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
        if os.path.exists(cleaned_audio):
            os.remove(cleaned_audio)
        logger.info("Pliki tymczasowe usunięte.")

if __name__ == "__main__":
    print("Script started...")  # Debug print
    if len(sys.argv) != 3:
        print("Użycie: python echo-removal.py input_video.mp4 output_video.mp4")
        sys.exit(1)

    input_video = sys.argv[1]
    output_video = sys.argv[2]

    # Sprawdzanie, czy plik wejściowy istnieje
    if not os.path.exists(input_video):
        logger.error(f"Plik wejściowy {input_video} nie istnieje!")
        sys.exit(1)

    logger.info(f"Plik wejściowy: {input_video}")
    logger.info(f"Plik wyjściowy: {output_video}")

# Dodaj dźwięk zakończenia
    import winsound
    winsound.Beep(1000, 500)  # Sygnał o częstotliwości 1000Hz trwający 500ms

    process_video(input_video, output_video)