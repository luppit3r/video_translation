import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

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
whisper = safe_import('whisper')

def extract_audio(video_path, audio_path):
    """Wyciąga audio z video z optymalnymi parametrami dla Whisper."""
    log(f"Starting audio extraction from {video_path}")
    if not os.path.exists(video_path):
        log(f"Error: Video file {video_path} does not exist")
        return False

    try:
        log("Running ffmpeg for audio extraction with optimized settings...")
        # Konwertuj ścieżki na stringi żeby uniknąć problemów z Path
        video_str = str(video_path)
        audio_str = str(audio_path)
        
        # Optymalne ustawienia dla Whisper: 16kHz, mono, wav
        (
            ffmpeg
            .input(video_str)
            .output(
                audio_str,
                acodec='pcm_s16le',  # 16-bit PCM
                ac=1,                # Mono
                ar='16000'           # 16kHz - optymalne dla Whisper
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

def transcribe_audio_with_whisper(audio_path, model_size="large-v2"):
    """Transkrybuje audio używając Whisper z optymalnymi ustawieniami dla polskiego."""
    log(f"Loading Whisper model '{model_size}' (this may take a moment)...")
    model = whisper.load_model(model_size)
    log("Whisper model loaded successfully")
    
    log(f"Starting transcription of {audio_path}")
    
    # Optymalne parametry dla polskiego języka
    result = model.transcribe(
        str(audio_path),
        language='pl',           # Wymuszamy polski język
        task='transcribe',       # Tylko transkrypcja (nie tłumaczenie)
        temperature=0.0,         # Deterministyczne wyniki
        best_of=5,              # Próbuje 5 razy i bierze najlepszy
        beam_size=5,            # Beam search dla lepszej jakości
        patience=1.0,           # Czeka na lepsze wyniki
        word_timestamps=True,   # Timestampy na poziomie słów
        condition_on_previous_text=True,  # Wykorzystuje kontekst
        compression_ratio_threshold=2.4,  # Filtruje powtórzenia
        logprob_threshold=-1.0,          # Filtruje niepewne fragmenty
        no_speech_threshold=0.6          # Filtruje ciszę
    )
    
    log("Transcription completed successfully")
    return result

def clean_text(text):
    """Czyści tekst z niepotrzebnych znaków i poprawia interpunkcję."""
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

def split_into_sentences(transcription_result):
    """Dzieli transkrypcję na zdania z dokładnymi timestampami."""
    log("Splitting transcription into sentences")
    sentences = []
    
    for segment in transcription_result['segments']:
        # Czyścimy tekst segmentu
        cleaned_text = clean_text(segment['text'])
        
        if cleaned_text:  # Tylko jeśli tekst nie jest pusty
            sentences.append({
                "start": round(segment['start'], 2),
                "end": round(segment['end'], 2),
                "sentence": cleaned_text
            })
    
    log(f"Split transcription into {len(sentences)} sentences")
    return sentences

def save_sentences_to_file(sentences, output_filename):
    """Zapisuje zdania do pliku w formacie zgodnym z oczekiwanym."""
    log(f"Saving sentences to {output_filename}")
    
    with open(output_filename, "w", encoding='utf-8') as f:
        for sentence in sentences:
            f.write(f"Start: {sentence['start']:.2f}, End: {sentence['end']:.2f}, Sentence: {sentence['sentence']}\n")
    
    log("Sentences saved successfully")

def process_video(input_path, model_size="large-v2"):
    """Główna funkcja przetwarzająca video."""
    log(f"Starting processing of video: {input_path}")
    
    try:
        input_path = Path(input_path)
        base_dir = input_path.parent
        
        # Tworzenie katalogów w strukturze zgodnej z głównym skryptem
        text_dir = base_dir / 'text'
        text_dir.mkdir(exist_ok=True)
        
        # Tymczasowy katalog na audio (będzie usunięty)
        temp_audio_dir = base_dir / 'temp_audio'
        temp_audio_dir.mkdir(exist_ok=True)
        
        log(f"Created output directories")

        # Ścieżki plików
        video_name = input_path.stem
        audio_path = temp_audio_dir / f"{video_name}.wav"
        transcription_path = text_dir / f"{video_name}_transcription.json"
        sentences_path = text_dir / f"{video_name}.txt"  # Zgodne z oczekiwanym formatem

        # Przetwarzanie
        if extract_audio(input_path, audio_path):
            transcription_result = transcribe_audio_with_whisper(audio_path, model_size)
            
            # Zapisz pełną transkrypcję JSON (opcjonalnie)
            log(f"Saving full transcription to {transcription_path}")
            with open(transcription_path, "w", encoding='utf-8') as f:
                json.dump(transcription_result, f, indent=4, ensure_ascii=False)
            
            # Zapisz zdania w oczekiwanym formacie
            sentences = split_into_sentences(transcription_result)
            save_sentences_to_file(sentences, sentences_path)
            
            # Usuń tymczasowe audio
            if audio_path.exists():
                audio_path.unlink()
                log("Temporary audio file removed")
            
            # Usuń tymczasowy katalog jeśli pusty
            try:
                temp_audio_dir.rmdir()
            except OSError:
                pass
            
            log(f"Processing complete for {input_path}")
            log(f"Transcription saved to: {sentences_path}")
            
            return str(sentences_path)
            
        else:
            log(f"Failed to process {input_path}")
            return None
            
    except Exception as e:
        log(f"An error occurred while processing {input_path}")
        log(f"Error details: {str(e)}")
        log("Stack trace:")
        log(traceback.format_exc())
        return None

def main():
    parser = argparse.ArgumentParser(description="Transcribe video files using Whisper with optimal settings for Polish.")
    parser.add_argument("input_path", help="Path to the video file")
    parser.add_argument("--model", default="large-v2", 
                       choices=["tiny", "base", "small", "medium", "large", "large-v2"],
                       help="Whisper model size (default: large-v2)")
    
    args = parser.parse_args()

    log("Starting improved video transcription")
    log(f"Input path: {args.input_path}")
    log(f"Using Whisper model: {args.model}")

    try:
        if os.path.isfile(args.input_path):
            result = process_video(args.input_path, args.model)
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

    log("Video transcription completed successfully")

if __name__ == "__main__":
    main()