import subprocess
import argparse
from pathlib import Path
import json
from datetime import datetime
import os

def add_intro_outro_fast(video_path, intro_path=None, outro_path=None, output_path=None):
    """
    Szybka wersja dodawania intro/outro używająca bezpośrednio ffmpeg.
    Znacznie szybsza od MoviePy bo używa stream copy zamiast rekodowania.
    """
    print(f"Szybkie przetwarzanie wideo: {video_path}")
    
    video_path = Path(video_path)
    
    # Ustaw domyślne ścieżki intro/outro
    if not intro_path:
        intro_path = "../intro_outro/Intro_EN.mp4"
    if not outro_path:
        outro_path = "../intro_outro/Outro_EN.mp4"
    
    intro_path = Path(intro_path)
    outro_path = Path(outro_path)
    
    # Ustaw ścieżkę wyjściową
    if not output_path:
        output_path = video_path.with_stem(video_path.stem + "_with_intro_outro_fast").with_suffix('.mp4')
    else:
        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix('.mp4')
    
    # Sprawdź czy pliki intro/outro istnieją
    files_to_concat = []
    
    if intro_path.exists():
        files_to_concat.append(str(intro_path))
        print(f"[OK] Znaleziono intro: {intro_path.name}")
    else:
        print(f"[UWAGA] Brak pliku intro: {intro_path}")
    
    # Główne wideo (zawsze)
    files_to_concat.append(str(video_path))
    print(f"[OK] Główne wideo: {video_path.name}")
    
    if outro_path.exists():
        files_to_concat.append(str(outro_path))
        print(f"[OK] Znaleziono outro: {outro_path.name}")
    else:
        print(f"[UWAGA] Brak pliku outro: {outro_path}")
    
    if len(files_to_concat) == 1:
        print("[BLAD] Brak plików intro/outro do dodania!")
        return None
    
    # Utwórz plik z listą plików do łączenia
    concat_file = video_path.parent / "concat_list.txt"
    
    try:
        with open(concat_file, 'w', encoding='utf-8') as f:
            for file_path in files_to_concat:
                # Konwertuj ścieżki na absolutne i escape'uj je
                abs_path = Path(file_path).resolve()
                # W ffmpeg concat file format używamy forward slashes nawet w Windows
                escaped_path = str(abs_path).replace('\\', '/')
                f.write(f"file '{escaped_path}'\n")
        
        print(f"Utworzono listę plików: {concat_file}")
        
        # Komenda ffmpeg z concat demuxer (najszybsza metoda)
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',  # Kopiuj strumienie bez rekodowania (bardzo szybkie!)
            '-avoid_negative_ts', 'make_zero',
            '-y',  # Nadpisz plik wyjściowy
            str(output_path)
        ]
        
        print("Uruchamianie ffmpeg...")
        print(f"Komenda: {' '.join(cmd)}")
        
        start_time = datetime.now()
        
        # Uruchom ffmpeg
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              text=True, 
                              cwd=str(video_path.parent))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if result.returncode == 0:
            print(f"\n[SUKCES] Wideo zostało pomyślnie utworzone w {duration:.1f} sekund!")
            print(f"[INFO] Plik zapisany: {output_path}")
            
            # Pokaż rozmiar pliku
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"[INFO] Rozmiar pliku: {size_mb:.1f} MB")
            
            return str(output_path)
        else:
            print(f"[BLAD] Błąd ffmpeg:")
            print(result.stderr)
            
            # Fallback do wolniejszej metody z rekodowaniem
            print("[INFO] Próbuję alternatywną metodę z rekodowaniem...")
            return add_intro_outro_with_reencoding(files_to_concat, output_path)
            
    finally:
        # Usuń tymczasowy plik
        if concat_file.exists():
            concat_file.unlink()
            print(f"[INFO] Usunięto tymczasowy plik: {concat_file.name}")

def add_intro_outro_with_reencoding(files_to_concat, output_path):
    """
    Fallback metoda z rekodowaniem gdy copy nie działa.
    """
    print("Używam metody z rekodowaniem (może trwać dłużej)...")
    
    # Utwórz input args dla ffmpeg
    input_args = []
    for file_path in files_to_concat:
        input_args.extend(['-i', file_path])
    
    # Filter complex do łączenia
    filter_complex = ""
    for i in range(len(files_to_concat)):
        filter_complex += f"[{i}:v][{i}:a]"
    filter_complex += f"concat=n={len(files_to_concat)}:v=1:a=1[outv][outa]"
    
    cmd = [
        'ffmpeg',
        *input_args,
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-c:a', 'aac',
        '-movflags', '+faststart',
        '-y',
        str(output_path)
    ]
    
    print(f"Komenda rekodowania: {' '.join(cmd)}")
    
    start_time = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if result.returncode == 0:
        print(f"\n[SUKCES] Wideo zostało utworzone z rekodowaniem w {duration:.1f} sekund!")
        print(f"[INFO] Plik zapisany: {output_path}")
        return str(output_path)
    else:
        print(f"[BLAD] Błąd podczas rekodowania:")
        print(result.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Szybko dodaj intro i outro do wideo używając ffmpeg")
    parser.add_argument("video_path", help="Ścieżka do głównego pliku wideo")
    parser.add_argument("--intro", help="Ścieżka do pliku intro (domyślnie: intro_outro/Intro_EN.mp4)")
    parser.add_argument("--outro", help="Ścieżka do pliku outro (domyślnie: intro_outro/Outro_EN.mp4)")
    parser.add_argument("--output", help="Ścieżka do pliku wyjściowego")
    
    args = parser.parse_args()
    
    # Sprawdź plik wideo
    video_path = Path(args.video_path)
    if not video_path.exists():
        print(f"[BLAD] Plik wideo nie istnieje: {video_path}")
        return
    
    try:
        result = add_intro_outro_fast(
            video_path=video_path,
            intro_path=args.intro,
            outro_path=args.outro,
            output_path=args.output
        )
        
        if result:
            print(f"\n[SUKCES] Proces zakończony pomyślnie!")
            print(f"[INFO] Wynikowy plik: {result}")
        else:
            print(f"\n[BLAD] Proces zakończony błędem!")
            
    except Exception as e:
        print(f"[BLAD] Nieoczekiwany błąd: {e}")
        return

if __name__ == "__main__":
    main()