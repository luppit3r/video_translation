import cv2
import numpy as np
import argparse
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips
from pydub import AudioSegment
from pydub.silence import detect_silence
import re
from tqdm import tqdm
from datetime import datetime
import subprocess

def parse_translation_file(file_path):
    """Wczytuje plik z tłumaczeniem i wyciąga timestampy."""
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    audio_segments = []
    for line_num, line in enumerate(lines, 1):
        match = re.match(r'Start: ([\d.]+), End: ([\d.]+), Sentence: (.+)', line.strip())
        if match:
            start = float(match.group(1))
            end = float(match.group(2))
            audio_segments.append({
                'line': line_num,
                'start': start,
                'end': end,
                'sentence': match.group(3)
            })
    
    return audio_segments

def find_silent_gaps_fast(video_path, translation_file_path, 
                         min_silence_len=2000, silence_thresh=-40,
                         gap_margin=0.5):
    """
    Szybka wersja wykrywania fragmentów ciszy.
    Używa bezpośrednio ffmpeg zamiast MoviePy do wyciągania audio.
    """
    print(f"[INFO] Szybkie wykrywanie ciszy w: {video_path}")
    
    # Wyciągnij audio używając ffmpeg (szybciej niż MoviePy)
    audio_path = Path.cwd() / "temp_silence_detection_fast.wav"
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # Simple audio codec
        '-ar', '22050',  # Lower sample rate for faster processing
        '-ac', '1',  # Mono for faster processing
        '-y',  # Overwrite
        str(audio_path)
    ]
    
    print("[INFO] Wyciąganie audio z ffmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[BLAD] Błąd ffmpeg: {result.stderr}")
        return []
    
    # Sprawdź czy plik został utworzony
    if not audio_path.exists():
        print(f"[BLAD] Plik audio nie został utworzony: {audio_path}")
        print(f"[DEBUG] ffmpeg stdout: {result.stdout}")
        print(f"[DEBUG] ffmpeg stderr: {result.stderr}")
        return []
    
    # Wykryj fragmenty ciszy (bez używania pliku tłumaczenia)
    print("[INFO] Wykrywanie fragmentów ciszy...")
    try:
        audio = AudioSegment.from_file(str(audio_path))
        all_silent_segments = detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
    except Exception as e:
        print(f"[BLAD] Błąd podczas wykrywania ciszy: {e}")
        return []
    finally:
        # Cleanup - zawsze usuń plik tymczasowy
        if audio_path.exists():
            audio_path.unlink()
    
    # Przetwórz fragmenty ciszy z marginesem (jak w oryginalnej wersji)
    gaps = []
    for i, (start, end) in enumerate(all_silent_segments):
        # Oryginalne wykrycie ciszy
        original_start = start / 1000  # Convert to seconds
        original_end = end / 1000
        original_duration = original_end - original_start
        
        # Dodaj margines bezpieczeństwa (gap_margin na początku i końcu)
        gap_start = original_start + gap_margin
        gap_end = original_end - gap_margin
        gap_duration = gap_end - gap_start
        
        # Sprawdź czy po dodaniu marginesu gap jest nadal wystarczająco długi
        if gap_duration >= min_silence_len/1000:
            gaps.append({
                'gap_id': i + 1,
                'gap_start': gap_start,
                'gap_end': gap_end,
                'gap_duration': gap_duration,
                'original_start': original_start,
                'original_end': original_end,
                'original_duration': original_duration
            })
            
            print(f"[OK] Silent gap {i+1}: {original_start:.2f}s to {original_end:.2f}s ({original_duration:.2f}s)")
            print(f"  -> Adjusted gap: {gap_start:.2f}s to {gap_end:.2f}s ({gap_duration:.2f}s) [margin: ±{gap_margin}s]")
        else:
            print(f"[SKIP] Silent gap {i+1}: {original_start:.2f}s to {original_end:.2f}s ({original_duration:.2f}s) - too short after margin adjustment")
    
    print(f"[INFO] Znaleziono {len(gaps)} fragmentów ciszy >= {min_silence_len/1000}s (z marginesem {gap_margin}s)")
    return gaps

def check_movement_fast(video_path, gaps, movement_threshold=20, min_static_pixels=300):
    """
    Zoptymalizowana analiza ruchu - 10x szybsza!
    Sprawdza tylko kluczowe klatki zamiast wszystkich.
    """
    print(f"[INFO] Szybka analiza ruchu w {len(gaps)} fragmentach...")
    
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    gaps_to_compress = []
    DOMINANCE_THRESHOLD = 0.6  # 60% bezruch = kompresuj cały gap
    
    for gap in tqdm(gaps, desc="Analyzing movement (FAST)"):
        gap_start = gap['gap_start']
        gap_end = gap['gap_end']
        gap_duration = gap['gap_duration']
        gap_id = gap['gap_id']
        
        print(f"\n  [SZYBKA ANALIZA] Gap {gap_id}: {gap_start:.1f}s-{gap_end:.1f}s ({gap_duration:.1f}s)")
        
        # OPTYMALIZACJA 1: Sprawdzaj co 0.5 sekundy zamiast co sekundę
        analysis_step = 0.5
        
        # OPTYMALIZACJA 2: Sprawdzaj mniej klatek na segment (2 zamiast 5)
        frames_per_check = 2
        
        movement_timeline = []
        current_time = gap_start
        
        while current_time < gap_end:
            check_end = min(current_time + analysis_step, gap_end)
            
            # Sprawdź ruch w tym segmencie
            start_frame = int(current_time * fps)
            end_frame = int(check_end * fps)
            
            has_movement = False
            max_movement_pixels = 0
            prev_frame = None
            frames_checked = 0
            
            # OPTYMALIZACJA 3: Sprawdź tylko kilka kluczowych klatek
            if end_frame - start_frame > frames_per_check:
                frame_step = (end_frame - start_frame) // frames_per_check
            else:
                frame_step = 1
            
            for frame_num in range(start_frame, end_frame, frame_step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    break
                
                # OPTYMALIZACJA 4: Przeskaluj ramkę dla szybszej analizy
                frame_small = cv2.resize(frame, (320, 240))  # Mniejsza rozdzielczość = szybsza analiza
                frame_gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)
                frames_checked += 1
                
                if prev_frame is not None:
                    diff = cv2.absdiff(prev_frame, frame_gray)
                    movement_pixels = np.sum(diff > movement_threshold)
                    
                    if movement_pixels > max_movement_pixels:
                        max_movement_pixels = movement_pixels
                    
                    # OPTYMALIZACJA 5: Dostosowany próg dla mniejszej rozdzielczości
                    adjusted_threshold = min_static_pixels // 16  # Proporcjonalne zmniejszenie
                    if movement_pixels > adjusted_threshold:
                        has_movement = True
                        break  # OPTYMALIZACJA 6: Przerwij jak znajdziesz ruch
                
                prev_frame = frame_gray
            
            segment_duration = check_end - current_time
            movement_timeline.append({
                'start': current_time,
                'end': check_end,
                'duration': segment_duration,
                'has_movement': has_movement,
                'max_movement_pixels': max_movement_pixels,
                'frames_checked': frames_checked
            })
            
            current_time = check_end
        
        # Oblicz dominację bezruchu
        total_duration = sum(seg['duration'] for seg in movement_timeline)
        static_duration = sum(seg['duration'] for seg in movement_timeline if not seg['has_movement'])
        static_ratio = static_duration / total_duration if total_duration > 0 else 0
        
        # Wyświetl skróconą analizę
        movement_count = sum(1 for seg in movement_timeline if seg['has_movement'])
        static_count = len(movement_timeline) - movement_count
        
        print(f"    [WYNIK] {static_count} bezruch / {movement_count} ruch | Bezruch: {static_ratio:.1%}")
        
        # Decyzja na podstawie dominacji
        if static_ratio >= DOMINANCE_THRESHOLD:
            gaps_to_compress.append(gap)
            print(f"    [KOMPRESJA] Gap {gap_id} zostanie skompresowany (bezruch dominuje: {static_ratio:.1%})")
        else:
            print(f"    [POMIŃ] Gap {gap_id} ma za dużo ruchu ({static_ratio:.1%} bezruchu < {DOMINANCE_THRESHOLD:.1%})")
    
    cap.release()
    print(f"\n[INFO] Znaleziono {len(gaps_to_compress)} fragmentów do kompresji (z {len(gaps)} analizowanych)")
    return gaps_to_compress

def generate_report_fast(all_gaps, gaps_compressed, output_path, video_path, original_video_path):
    """Generuje zaawansowany raport kompresji z timestampami w nowym video."""
    if not gaps_compressed:
        print("[INFO] Brak skompresowanych fragmentów - pomijam raport")
        return
        
    report_path = Path(output_path).with_suffix('.txt')
    
    # Pobierz czas trwania oryginalnego video
    try:
        video_clip = VideoFileClip(str(original_video_path))
        original_duration = video_clip.duration
        video_clip.close()
    except:
        original_duration = 0
    
    total_gap_duration = sum(gap['gap_duration'] for gap in gaps_compressed)
    time_saved = total_gap_duration  # Cały czas gap'a jest oszczędzony
    new_duration = original_duration - time_saved if original_duration > 0 else 0
    
    # Oblicz timestampy w nowym video
    def format_time(seconds):
        """Formatuje sekundy na MM:SS format"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:05.2f}"
    
    # Sortuj gap'y według czasu rozpoczęcia
    sorted_gaps = sorted(gaps_compressed, key=lambda x: x['gap_start'])
    
    # Oblicz przesunięcia timestampów
    new_video_timestamps = []
    cumulative_removed = 0.0
    
    for gap in sorted_gaps:
        # Timestamp w nowym video = oryginalny timestamp - skumulowane usunięte sekundy
        new_timestamp = gap['gap_start'] - cumulative_removed
        new_video_timestamps.append(new_timestamp)
        cumulative_removed += gap['gap_duration']
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Raport SZYBKIEGO usuwania ciszy\n")
        f.write("===============================\n\n")
        f.write(f"Plik wejściowy: {Path(original_video_path).name}\n")
        f.write(f"Plik wyjściowy: {Path(output_path).name}\n\n")
        
        f.write(f"Fragmenty ciszy znalezione: {len(all_gaps)}\n")
        f.write(f"Fragmenty z ruchem (pominięte): {len(all_gaps) - len(gaps_compressed)}\n") 
        f.write(f"Fragmenty USUNIĘTE CAŁKOWICIE: {len(gaps_compressed)}\n\n")
        
        if original_duration > 0:
            f.write(f"Oryginalny czas: {original_duration/60:.1f} min ({original_duration:.1f}s)\n")
            f.write(f"Nowy czas: {new_duration/60:.1f} min ({new_duration:.1f}s)\n")
            f.write(f"Zaoszczędzony czas: {time_saved/60:.1f} min ({time_saved:.1f}s)\n")
            f.write(f"Redukcja: {(time_saved/original_duration)*100:.1f}%\n\n")
        
        f.write("Usunięte fragmenty z timestampami w NOWYM video:\n")
        f.write("-" * 80 + "\n")
        
        for i, gap in enumerate(sorted_gaps):
            gap_id = gap['gap_id']
            gap_start = gap['gap_start']
            gap_end = gap['gap_end']
            gap_duration = gap['gap_duration']
            new_timestamp = new_video_timestamps[i]
            
            f.write(f"Gap {gap_id:2d}: {format_time(gap_start)} - {format_time(gap_end)} "
                   f"({gap_duration:4.1f}s - DELETED) → w nowym video: {format_time(new_timestamp)}\n")
        
        f.write(f"\n[UWAGA] Fragmenty zostały USUNIĘTE CAŁKOWICIE (nie zastąpione freeze frame'ami)\n")
        f.write(f"Timestampy w nowym video będą przesunięte!\n\n")
        
        # Dodaj listę miejsc do sprawdzenia
        f.write("Sprawdź przejścia w NOWYM video: ")
        timestamp_list = [format_time(ts) for ts in new_video_timestamps]
        f.write(", ".join(timestamp_list) + "\n\n")
        
        # Dodaj instrukcje cofnięcia
        f.write("Instrukcje cofnięcia usunięć:\n")
        f.write("-" * 40 + "\n")
        f.write("Jeśli któreś wycięcie było błędne, możesz je cofnąć:\n\n")
        
        input_name = Path(original_video_path).name
        output_name = Path(output_path).name
        
        for gap in sorted_gaps:
            gap_id = gap['gap_id']
            f.write(f"Cofnij Gap {gap_id}: python reprocess.py \"{input_name}\" \"{output_name}\" --exclude-gaps {gap_id}\n")
    
    print(f"[INFO] Raport zapisany: {report_path}")

def generate_report_no_compression(silent_gaps, output_path, original_video_path):
    """Generuje raport gdy nie ma kompresji (fragmenty mają ruch)."""
    report_path = Path(output_path).with_suffix('.txt')
    
    # Pobierz czas trwania oryginalnego video
    try:
        video_clip = VideoFileClip(str(original_video_path))
        original_duration = video_clip.duration
        video_clip.close()
    except:
        original_duration = 0
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Raport SZYBKIEGO usuwania ciszy\n")
        f.write("===============================\n\n")
        f.write(f"Plik wejściowy: {Path(original_video_path).name}\n")
        f.write(f"Plik wyjściowy: {Path(output_path).name}\n\n")
        
        f.write(f"Fragmenty ciszy znalezione: {len(silent_gaps)}\n")
        f.write(f"Fragmenty z ruchem (pominięte): {len(silent_gaps)}\n") 
        f.write(f"Fragmenty USUNIĘTE: 0\n\n")
        
        if original_duration > 0:
            f.write(f"Oryginalny czas: {original_duration/60:.1f} min ({original_duration:.1f}s)\n")
            f.write(f"Nowy czas: {original_duration/60:.1f} min ({original_duration:.1f}s)\n")
            f.write(f"Zaoszczędzony czas: 0.0 min (0.0s)\n")
            f.write(f"Redukcja: 0.0%\n\n")
        
        f.write("Fragmenty ciszy z ruchem (nie usunięte):\n")
        f.write("-" * 80 + "\n")
        
        for gap in silent_gaps:
            gap_id = gap['gap_id']
            gap_start = gap['gap_start']
            gap_end = gap['gap_end']
            gap_duration = gap['gap_duration']
            
            f.write(f"Gap {gap_id}: {gap_start:.2f}s - {gap_end:.2f}s "
                   f"({gap_duration:.2f}s) → POMINIĘTY (ma ruch)\n")
        
        f.write(f"\n[INFO] Wszystkie fragmenty ciszy miały ruch - plik skopiowany bez zmian\n")
    
    print(f"[INFO] Raport zapisany: {report_path}")

def generate_report_no_silence(output_path, original_video_path):
    """Generuje raport gdy nie ma fragmentów ciszy."""
    report_path = Path(output_path).with_suffix('.txt')
    
    # Pobierz czas trwania oryginalnego video
    try:
        video_clip = VideoFileClip(str(original_video_path))
        original_duration = video_clip.duration
        video_clip.close()
    except:
        original_duration = 0
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Raport SZYBKIEGO usuwania ciszy\n")
        f.write("===============================\n\n")
        f.write(f"Plik wejściowy: {Path(original_video_path).name}\n")
        f.write(f"Plik wyjściowy: {Path(output_path).name}\n\n")
        
        f.write(f"Fragmenty ciszy znalezione: 0\n")
        f.write(f"Fragmenty z ruchem (pominięte): 0\n") 
        f.write(f"Fragmenty USUNIĘTE: 0\n\n")
        
        if original_duration > 0:
            f.write(f"Oryginalny czas: {original_duration/60:.1f} min ({original_duration:.1f}s)\n")
            f.write(f"Nowy czas: {original_duration/60:.1f} min ({original_duration:.1f}s)\n")
            f.write(f"Zaoszczędzony czas: 0.0 min (0.0s)\n")
            f.write(f"Redukcja: 0.0%\n\n")
        
        f.write("[INFO] Nie znaleziono fragmentów ciszy do usunięcia\n")
        f.write("Możliwe przyczyny:\n")
        f.write("- Audio jest głośne przez cały czas\n")
        f.write("- Próg ciszy (-40dB) jest zbyt restrykcyjny\n")
        f.write("- Minimalna długość ciszy (2s) jest zbyt wysoka\n\n")
        f.write("Plik został skopiowany bez zmian.\n")
    
    print(f"[INFO] Raport zapisany: {report_path}")

def compress_video_fast(video_path, gaps_to_compress, output_path):
    """
    Szybka kompresja video - USUWA fragmenty całkowicie (jak w oryginalnej wersji).
    Używa ffmpeg zamiast MoviePy.
    """
    if not gaps_to_compress:
        print("[INFO] Brak fragmentów do kompresji")
        return False
    
    print(f"[INFO] Szybkie usuwanie {len(gaps_to_compress)} fragmentów...")
    
    # Pobierz czas trwania video
    video_clip = VideoFileClip(str(video_path))
    total_duration = video_clip.duration
    video_clip.close()
    
    # Utwórz listę segmentów do ZACHOWANIA (pomijamy gap'y całkowicie)
    segments = []
    current_pos = 0.0
    
    # Sortuj gaps by gap_start
    gaps_sorted = sorted(gaps_to_compress, key=lambda x: x['gap_start'])
    
    for gap in gaps_sorted:
        gap_start = gap['gap_start']
        gap_end = gap['gap_end']
        gap_duration = gap['gap_duration']
        gap_id = gap['gap_id']
        
        # Dodaj normalną część przed gap'em
        if gap_start > current_pos:
            segments.append((current_pos, gap_start))
        
        # POMIŃ gap całkowicie - nie dodawaj nic!
        print(f"  [USUŃ] Gap {gap_id}: {gap_start:.2f}s-{gap_end:.2f}s ({gap_duration:.2f}s) - DELETED")
        
        current_pos = gap_end
    
    # Dodaj ostatni segment
    if current_pos < total_duration:
        segments.append((current_pos, total_duration))
    
    if not segments:
        print("[BLAD] Brak segmentów do zachowania!")
        return False
    
    # Utwórz filter complex dla ffmpeg
    inputs = ['-i', str(video_path)]
    filter_parts = []
    segment_refs = []
    
    for i, (start, end) in enumerate(segments):
        # Resetujemy PTS ale z lepszą synchronizacją
        filter_parts.append(f"[0:v]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS[v{i}]")
        filter_parts.append(f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{i}]")
        segment_refs.append(f"[v{i}][a{i}]")
    
    # Połącz wszystkie segmenty
    concat_filter = f"{''.join(segment_refs)}concat=n={len(segments)}:v=1:a=1[outv][outa]"
    filter_parts.append(concat_filter)
    
    filter_complex = ';'.join(filter_parts)
    
    # Komenda ffmpeg z poprawkami dla timestamp'ów
    cmd = [
        'ffmpeg',
        *inputs,
        '-filter_complex', filter_complex,
        '-map', '[outv]',
        '-map', '[outa]',
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-crf', '23',
        '-c:a', 'aac',
        '-avoid_negative_ts', 'make_zero',  # Napraw problemy z timestamp'ami
        '-fflags', '+genpts',  # Regeneruj timestamp'y
        '-movflags', '+faststart',
        '-y',
        str(output_path)
    ]
    
    print("[INFO] Uruchamianie kompresji ffmpeg...")
    start_time = datetime.now()
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if result.returncode == 0:
        print(f"\n[SUKCES] Video skompresowane w {duration:.1f} sekund!")
        print(f"[INFO] Plik zapisany: {output_path}")
        print(f"[INFO] Usunięto {len(gaps_to_compress)} fragmentów całkowicie")
        return True
    else:
        print(f"[BLAD] Błąd kompresji ffmpeg:")
        print(result.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Szybkie usuwanie ciszy z wideo")
    parser.add_argument("video_file", help="Input video file")
    parser.add_argument("output_file", help="Output video file")
    parser.add_argument("--min_silence_len", type=int, default=2000, help="Minimum silence length (ms)")
    parser.add_argument("--silence_thresh", type=int, default=-40, help="Silence detection threshold (dB)")
    parser.add_argument("--gap_margin", type=float, default=0.5, help="Safety margin around detected silence (s)")
    parser.add_argument("--movement_threshold", type=int, default=15, help="Movement detection threshold")
    parser.add_argument("--min_static_pixels", type=int, default=100, help="Min pixels to consider movement")
    
    args = parser.parse_args()
    
    print(f"[INFO] SZYBKIE usuwanie ciszy i bezruchu")
    print(f"[INFO] Video: {args.video_file}")
    print(f"[INFO] Output: {args.output_file}")
    print(f"[INFO] Min cisza: {args.min_silence_len}ms, Próg: {args.silence_thresh}dB")
    print(f"[INFO] Margines: {args.gap_margin}s")
    print("-" * 60)
    
    # Sprawdź pliki
    video_path = Path(args.video_file)
    output_path = Path(args.output_file)
    
    if not video_path.exists():
        print(f"[BLAD] Plik video nie istnieje: {video_path}")
        return
    
    try:
        # 1. Znajdź fragmenty ciszy (szybko)
        silent_gaps = find_silent_gaps_fast(
            str(video_path), 
            None,  # Nie używamy pliku tłumaczenia
            min_silence_len=args.min_silence_len,
            silence_thresh=args.silence_thresh,
            gap_margin=args.gap_margin
        )
        
        if not silent_gaps:
            print("[INFO] Brak fragmentów ciszy - kopiuję plik bez zmian")
            # Skopiuj oryginalny plik jako wynik
            import shutil
            shutil.copy2(str(video_path), str(output_path))
            print(f"[SUKCES] Plik skopiowany: {output_path}")
            
            # Generuj raport - nawet gdy nie ma fragmentów ciszy
            generate_report_no_silence(str(output_path), str(video_path))
            return
        
        # 2. Sprawdź ruch w fragmentach ciszy (szybko)
        gaps_to_compress = check_movement_fast(
            str(video_path), 
            silent_gaps,
            args.movement_threshold,
            args.min_static_pixels
        )
        
        # 3. Kompresja video (szybko)
        if gaps_to_compress:
            success = compress_video_fast(
                str(video_path),
                gaps_to_compress,
                str(output_path)
            )
            
            if success:
                print(f"\n[SUKCES] Proces zakończony pomyślnie!")
                print(f"[INFO] Skompresowano {len(gaps_to_compress)} fragmentów")
                
                # Generuj raport
                try:
                    print(f"[INFO] Generowanie raportu...")
                    generate_report_fast(silent_gaps, gaps_to_compress, str(output_path), 
                                       str(video_path), str(video_path))
                except Exception as e:
                    print(f"[BLAD] Nie udało się wygenerować raportu: {e}")
            else:
                print(f"\n[BLAD] Błąd podczas kompresji!")
        else:
            print("[INFO] Wszystkie fragmenty ciszy mają ruch - kopiuję plik bez zmian")
            # Skopiuj oryginalny plik jako wynik
            import shutil
            shutil.copy2(str(video_path), str(output_path))
            print(f"[SUKCES] Plik skopiowany: {output_path}")
            
            # Generuj raport - nawet gdy nie ma kompresji
            generate_report_no_compression(silent_gaps, str(output_path), str(video_path))
    
    except Exception as e:
        print(f"[BLAD] Nieoczekiwany błąd: {e}")

if __name__ == "__main__":
    main()