import subprocess
import argparse
from pathlib import Path
import json
import re
from datetime import datetime

def read_translated_file(file_path):
    """Wczytuje plik z timestampami i zdaniami."""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    timestamps = []
    sentences = []
    for line in lines:
        # Use regular expressions to extract start, end, and sentence
        match = re.match(r'Start: ([\d.]+), End: ([\d.]+), Sentence: (.+)', line)
        if match:
            start = float(match.group(1))
            end = float(match.group(2))
            sentence = match.group(3).strip()
            timestamps.append((start, end))
            sentences.append(sentence)

    return timestamps, sentences

def overlay_audio_fast(video_file_path, timestamps, audio_dir, output_video_path):
    """
    Szybka wersja nakładania audio używająca bezpośrednio ffmpeg.
    Znacznie szybsza od MoviePy.
    """
    print(f"[INFO] Szybkie nakładanie audio na video: {video_file_path}")
    video_file_path = Path(video_file_path)
    audio_dir = Path(audio_dir)
    output_video_path = Path(output_video_path)
    
    # Sprawdź czy wszystkie pliki audio istnieją
    missing_files = []
    audio_files = []
    
    for i, (start, end) in enumerate(timestamps):
        audio_file = audio_dir / f"output_audio_{i}.mp3"
        if audio_file.exists():
            audio_files.append((audio_file, start, end))
            print(f"[OK] Audio {i}: {audio_file.name} -> {start:.2f}s")
        else:
            missing_files.append(f"output_audio_{i}.mp3")
    
    if missing_files:
        print(f"[BLAD] Brakuje plików audio: {', '.join(missing_files)}")
        return False
    
    if not audio_files:
        print("[BLAD] Brak plików audio do przetworzenia!")
        return False
    
    print(f"[INFO] Znaleziono {len(audio_files)} plików audio")
    
    # Utwórz filter complex dla ffmpeg
    inputs = ['-i', str(video_file_path)]
    filter_parts = []
    audio_inputs = []
    
    # Dodaj wszystkie pliki audio jako inputy
    for i, (audio_file, start, end) in enumerate(audio_files):
        inputs.extend(['-i', str(audio_file)])
        audio_inputs.append(f"[{i+1}:a]")
        # Opóźnij audio o odpowiedni czas
        filter_parts.append(f"[{i+1}:a]adelay={int(start*1000)}|{int(start*1000)}[a{i}]")
    
    # Połącz wszystkie audio z opóźnieniami
    if len(audio_files) == 1:
        mix_filter = filter_parts[0].replace(f"[a0]", "[mixed]")
    else:
        # Miksuj wszystkie audio razem
        audio_refs = ''.join([f"[a{i}]" for i in range(len(audio_files))])
        filter_parts.append(f"{audio_refs}amix=inputs={len(audio_files)}:duration=longest[mixed]")
    
    # Kompletny filter complex
    filter_complex = ';'.join(filter_parts)
    
    # Komenda ffmpeg
    cmd = [
        'ffmpeg',
        *inputs,
        '-filter_complex', filter_complex,
        '-map', '0:v',  # Video z pierwszego inputu
        '-map', '[mixed]',  # Zmiksowane audio
        '-c:v', 'copy',  # Kopiuj video bez rekodowania (szybko!)
        '-c:a', 'aac',   # Koduj audio do AAC
        '-shortest',     # Zakończ gdy najkrótszy stream się skończy
        '-y',           # Nadpisz plik wyjściowy
        str(output_video_path)
    ]
    
    print("[INFO] Uruchamianie ffmpeg...")
    print(f"[DEBUG] Komenda: {' '.join(cmd[:10])}... (skrócone)")
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              text=True, 
                              cwd=str(video_file_path.parent))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result.returncode == 0:
            print(f"\n[SUKCES] Audio zostało nałożone w {duration:.1f} sekund!")
            print(f"[INFO] Plik zapisany: {output_video_path}")
            
            # Pokaż rozmiar pliku
            if output_video_path.exists():
                size_mb = output_video_path.stat().st_size / (1024 * 1024)
                print(f"[INFO] Rozmiar pliku: {size_mb:.1f} MB")
            
            return True
        else:
            print(f"[BLAD] Błąd ffmpeg:")
            print(result.stderr)
            
            # Fallback do MoviePy jeśli ffmpeg nie zadziała
            print("[INFO] Próbuję fallback do MoviePy...")
            return overlay_audio_moviepy_fallback(video_file_path, timestamps, audio_dir, output_video_path)
            
    except Exception as e:
        print(f"[BLAD] Błąd uruchamiania ffmpeg: {e}")
        print("[INFO] Próbuję fallback do MoviePy...")
        return overlay_audio_moviepy_fallback(video_file_path, timestamps, audio_dir, output_video_path)

def overlay_audio_moviepy_fallback(video_file_path, timestamps, audio_dir, output_video_path):
    """
    Fallback do MoviePy gdy ffmpeg nie działa.
    """
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
        print("[INFO] Używam MoviePy jako fallback...")
        
        start_time = datetime.now()
        
        video_clip = VideoFileClip(str(video_file_path))
        audio_clips = []
        
        # Wczytaj pliki audio
        for i, (start, end) in enumerate(timestamps):
            audio_file_path = audio_dir / f"output_audio_{i}.mp3"
            if audio_file_path.exists():
                audio_clip = AudioFileClip(str(audio_file_path))
                audio_clip = audio_clip.set_start(start)
                audio_clips.append(audio_clip)
        
        # Połącz audio
        final_audio = CompositeAudioClip(audio_clips)
        final_video = video_clip.set_audio(final_audio)
        
        # Zapisz z optymalizowanymi ustawieniami
        final_video.write_videofile(
            str(output_video_path),
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None,
            preset='veryfast',  # Szybsze kodowanie
            threads=8,  # Więcej wątków
            ffmpeg_params=['-crf', '23', '-movflags', '+faststart']
        )
        
        # Cleanup
        final_video.close()
        video_clip.close()
        final_audio.close()
        for clip in audio_clips:
            clip.close()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"[SUKCES] Audio nałożone z MoviePy w {duration:.1f} sekund!")
        return True
        
    except Exception as e:
        print(f"[BLAD] Błąd MoviePy fallback: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Szybko nałóż audio na video używając ffmpeg")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("video_file", help="Path to the input video file")
    parser.add_argument("--audio_dir", default="generated", help="Directory containing generated audio files")
    args = parser.parse_args()

    input_file = Path(args.input_file)
    video_file = Path(args.video_file)
    
    # Adjust audio_dir to be relative to the main directory
    main_dir = input_file.parents[1]
    audio_dir = Path(args.audio_dir) if Path(args.audio_dir).is_absolute() else main_dir / args.audio_dir / video_file.stem

    # Create output directory in the main folder
    output_dir = main_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_video_path = output_dir / f"{video_file.stem}_synchronized.mp4"

    # Sprawdź pliki
    if not input_file.exists():
        print(f"[BLAD] Plik tłumaczenia nie istnieje: {input_file}")
        return
    
    if not video_file.exists():
        print(f"[BLAD] Plik video nie istnieje: {video_file}")
        return
    
    if not audio_dir.exists():
        print(f"[BLAD] Folder audio nie istnieje: {audio_dir}")
        return

    timestamps, _ = read_translated_file(input_file)
    
    if not timestamps:
        print("[BLAD] Brak timestampów w pliku tłumaczenia!")
        return

    try:
        success = overlay_audio_fast(video_file, timestamps, audio_dir, output_video_path)
        
        if success:
            print(f"\n[SUKCES] Proces zakończony pomyślnie!")
            print(f"[INFO] Wynikowy plik: {output_video_path}")
        else:
            print(f"\n[BLAD] Proces zakończony błędem!")
            
    except Exception as e:
        print(f"[BLAD] Nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    main()