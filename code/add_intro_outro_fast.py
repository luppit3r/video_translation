import subprocess
import argparse
from pathlib import Path
import json
from datetime import datetime
import os

def add_intro_outro_fast(video_path, intro_path=None, outro_path=None, output_path=None):
    """
    Szybka wersja dodawania intro/outro używająca bezpośrednio ffmpeg.
    Używa filter_complex dla stabilnego łączenia plików.
    """
    print(f"Szybkie przetwarzanie wideo: {video_path}")
    
    video_path = Path(video_path)
    
    # Ustaw domyślne ścieżki intro/outro - szukaj w różnych lokalizacjach
    if not intro_path:
        # Możliwe lokalizacje intro/outro
        possible_intro_paths = [
            "../intro_outro/Intro_EN.mp4",  # Standardowa ścieżka
            "../../intro_outro/Intro_EN.mp4",  # Z podfolderu output
            "../../../intro_outro/Intro_EN.mp4",  # Z głębszego poziomu
            Path(__file__).parent.parent / "intro_outro" / "Intro_EN.mp4",  # Względem skryptu
            Path(__file__).parent.parent.parent / "intro_outro" / "Intro_EN.mp4",  # Z folderu głównego projektu
        ]
        intro_path = None
        for path in possible_intro_paths:
            if Path(path).exists():
                intro_path = str(path)
                break
        if not intro_path:
            intro_path = "../intro_outro/Intro_EN.mp4"  # Fallback
    
    if not outro_path:
        # Możliwe lokalizacje intro/outro
        possible_outro_paths = [
            "../intro_outro/Outro_EN.mp4",  # Standardowa ścieżka
            "../../intro_outro/Outro_EN.mp4",  # Z podfolderu output
            "../../../intro_outro/Outro_EN.mp4",  # Z głębszego poziomu
            Path(__file__).parent.parent / "intro_outro" / "Outro_EN.mp4",  # Względem skryptu
            Path(__file__).parent.parent.parent / "intro_outro" / "Outro_EN.mp4",  # Z folderu głównego projektu
        ]
        outro_path = None
        for path in possible_outro_paths:
            if Path(path).exists():
                outro_path = str(path)
                break
        if not outro_path:
            outro_path = "../intro_outro/Outro_EN.mp4"  # Fallback
    
    intro_path = Path(intro_path)
    outro_path = Path(outro_path)
    
    # Ustaw ścieżkę wyjściową
    if not output_path:
        output_path = video_path.with_stem(video_path.stem + "_with_intro_outro_fast").with_suffix('.mp4')
    else:
        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix('.mp4')
    
    # Sprawdź które pliki istnieją
    input_files = []
    filter_inputs = []
    
    if intro_path.exists():
        input_files.append(str(intro_path))
        filter_inputs.append("[0:v][0:a]")
        print(f"[OK] Znaleziono intro: {intro_path.name}")
    else:
        print(f"[UWAGA] Brak pliku intro: {intro_path}")
    
    # Główne wideo (zawsze)
    input_files.append(str(video_path))
    current_index = len(input_files) - 1
    filter_inputs.append(f"[{current_index}:v][{current_index}:a]")
    print(f"[OK] Główne wideo: {video_path.name}")
    
    if outro_path.exists():
        input_files.append(str(outro_path))
        current_index = len(input_files) - 1
        filter_inputs.append(f"[{current_index}:v][{current_index}:a]")
        print(f"[OK] Znaleziono outro: {outro_path.name}")
    else:
        print(f"[UWAGA] Brak pliku outro: {outro_path}")
    
    if len(input_files) == 1:
        print("[BLAD] Brak plików intro/outro do dodania!")
        return None
    
    # Buduj komendę ffmpeg z filter_complex
    cmd = ['ffmpeg']
    
    # Dodaj wszystkie pliki wejściowe
    for file_path in input_files:
        cmd.extend(['-i', file_path])
    
    # Utwórz filter_complex
    filter_complex = "".join(filter_inputs) + f"concat=n={len(input_files)}:v=1:a=1[outv][outa]"
    
    cmd.extend([
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'libx264',  # Rekodowanie potrzebne dla filter_complex
        '-c:a', 'aac',
        '-crf', '23',  # Dobra jakość
        '-preset', 'fast',  # Szybkie kodowanie
        '-avoid_negative_ts', 'make_zero',
        '-y',  # Nadpisz plik wyjściowy
        str(output_path)
    ])
    
    print("Uruchamianie ffmpeg z filter_complex...")
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
        print(f"[BLAD] Stdout: {result.stdout}")
        return None

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