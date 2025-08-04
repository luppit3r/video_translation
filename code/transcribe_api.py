import os
import sys
import time
import traceback
from pathlib import Path
import argparse

def log(message):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def safe_import(module_name):
    try:
        return __import__(module_name)
    except ImportError as e:
        log(f"Error importing {module_name}: {e}")
        log(f"Please ensure {module_name} is installed correctly in your virtual environment.")
        sys.exit(1)

ffmpeg = safe_import('ffmpeg')

# Importuj OpenAI
try:
    from openai import OpenAI
except ImportError:
    log("Installing OpenAI client...")
    os.system("pip install openai")
    from openai import OpenAI

def extract_audio(video_path, audio_path):
    """Wyciąga audio z video dla API OpenAI."""
    log(f"Starting audio extraction from {video_path}")
    if not os.path.exists(video_path):
        log(f"Error: Video file {video_path} does not exist")
        return False

    try:
        log("Running ffmpeg for audio extraction...")
        # API OpenAI preferuje mp3
        (
            ffmpeg
            .input(str(video_path))
            .output(
                str(audio_path),
                acodec='mp3',
                ar='16000'  # 16kHz
            )
            .run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        )
        log("Audio extraction successful")
        return True
    except ffmpeg.Error as e:
        log(f"Error occurred during audio extraction: {e.stderr.decode('utf-8')}")
        return False
    except Exception as e:
        log(f"Unexpected error during audio extraction: {str(e)}")
        return False

def transcribe_with_openai_api(audio_path, api_key):
    """Transkrybuje audio używając OpenAI API."""
    log("Starting transcription using OpenAI API...")
    
    client = OpenAI(api_key=api_key)
    
    try:
        with open(audio_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="pl",  # Polski
                response_format="verbose_json",  # Zawiera timestampy
                timestamp_granularities=["segment"]
            )
        
        log("Transcription completed successfully")
        return transcript
        
    except Exception as e:
        log(f"Error during API transcription: {str(e)}")
        return None

def convert_api_response_to_segments(transcript):
    """Konwertuje odpowiedź API na format segmentów."""
    segments = []
    
    if hasattr(transcript, 'segments') and transcript.segments:
        for segment in transcript.segments:
            segments.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "sentence": segment.text.strip()
            })
    else:
        # Fallback - jeden duży segment
        segments.append({
            "start": 0.00,
            "end": 0.00,
            "sentence": transcript.text.strip()
        })
    
    log(f"Converted to {len(segments)} segments")
    return segments

def clean_text(text):
    """Czyści tekst z niepotrzebnych znaków."""
    import re
    
    # Usuń nadmiarowe spacje
    text = re.sub(r'\s+', ' ', text)
    
    # Popraw interpunkcję
    text = text.replace(' ,', ',')
    text = text.replace(' .', '.')
    text = text.replace(' !', '!')
    text = text.replace(' ?', '?')
    
    # Pierwsza litera wielka
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:]
    
    return text.strip()

def save_sentences_to_file(sentences, output_filename):
    """Zapisuje zdania do pliku w oczekiwanym formacie."""
    log(f"Saving sentences to {output_filename}")
    
    with open(output_filename, "w", encoding='utf-8') as f:
        for sentence in sentences:
            clean_sentence = clean_text(sentence["sentence"])
            f.write(f"Start: {sentence['start']:.2f}, End: {sentence['end']:.2f}, Sentence: {clean_sentence}\n")
    
    log("Sentences saved successfully")

def process_video_api(input_path, api_key):
    """Główna funkcja przetwarzająca video przez API."""
    log(f"Starting API processing of video: {input_path}")
    
    try:
        input_path = Path(input_path)
        base_dir = input_path.parent
        
        # Tworzenie katalogów
        text_dir = base_dir / 'text'
        text_dir.mkdir(exist_ok=True)
        
        temp_audio_dir = base_dir / 'temp_audio'
        temp_audio_dir.mkdir(exist_ok=True)
        
        log("Created output directories")

        # Ścieżki plików
        video_name = input_path.stem
        audio_path = temp_audio_dir / f"{video_name}.mp3"  # MP3 dla API
        sentences_path = text_dir / f"{video_name}_sentences.txt"

        # Przetwarzanie
        if extract_audio(input_path, audio_path):
            transcript = transcribe_with_openai_api(audio_path, api_key)
            
            if transcript:
                # Konwertuj na format segmentów
                sentences = convert_api_response_to_segments(transcript)
                save_sentences_to_file(sentences, sentences_path)
                
                # Usuń tymczasowe audio
                if audio_path.exists():
                    audio_path.unlink()
                    log("Temporary audio file removed")
                
                # Usuń tymczasowy katalog
                try:
                    temp_audio_dir.rmdir()
                except OSError:
                    pass
                
                log(f"Processing complete for {input_path}")
                log(f"Transcription saved to: {sentences_path}")
                
                return str(sentences_path)
            else:
                log("API transcription failed!")
                return None
        else:
            log(f"Failed to extract audio from {input_path}")
            return None
            
    except Exception as e:
        log(f"An error occurred while processing {input_path}")
        log(f"Error details: {str(e)}")
        log("Stack trace:")
        log(traceback.format_exc())
        return None

def main():
    # Hardkodowany klucz (taki sam jak w process_video.py)
    OPENAI_API_KEY = "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"
    
    parser = argparse.ArgumentParser(description="Transcribe video using OpenAI API")
    parser.add_argument("input_path", help="Path to the video file")
    parser.add_argument("--api-key", help="OpenAI API key (optional, has default)")
    
    args = parser.parse_args()

    # Pobierz klucz API (domyślnie hardkodowany)
    api_key = args.api_key or os.getenv('OPENAI_API_KEY') or OPENAI_API_KEY
    if not api_key:
        log("ERROR: No API key available!")
        sys.exit(1)

    log("Starting OpenAI API video transcription")
    log(f"Input path: {args.input_path}")

    try:
        if os.path.isfile(args.input_path):
            result = process_video_api(args.input_path, api_key)
            if result:
                log(f"Success! Transcription saved to: {result}")
            else:
                log("Transcription failed!")
                sys.exit(1)
        else:
            log(f"Error: Invalid input path: {args.input_path}")
            sys.exit(1)
            
    except Exception as e:
        log(f"An unexpected error occurred: {str(e)}")
        log("Stack trace:")
        log(traceback.format_exc())
        sys.exit(1)

    log("API transcription completed successfully")

if __name__ == "__main__":
    main()