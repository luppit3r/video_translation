import argparse
import re
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageClip, AudioFileClip
from pydub import AudioSegment, silence
from pathlib import Path
from tqdm import tqdm

def parse_existing_report(report_path):
    """Czyta istniejący raport z delete_sm.py i wyciąga dane o gap'ach."""
    print(f"Reading existing report: {report_path}")
    
    if not Path(report_path).exists():
        print(f"Error: Report file not found: {report_path}")
        return None, None
    
    gaps_data = []
    original_video = None
    processed_video = None
    
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Wyciągnij nazwy plików
    file_match = re.search(r'Plik wejściowy: (.+)', content)
    if file_match:
        original_video = file_match.group(1).strip()
    
    output_match = re.search(r'Plik wyjściowy: (.+)', content)
    if output_match:
        processed_video = output_match.group(1).strip()
    
    # Znajdź sekcję ze skompresowanymi gaps
    gaps_section = re.search(r'Usunięte gaps.*?\n-+\n(.*?)\n\nSprawdź przejścia', content, re.DOTALL)
    if not gaps_section:
        print("Error: Could not find gaps data in report")
        return None, None
    
    gaps_text = gaps_section.group(1)
    
    # Parse każdej linii gap'a
    # Format: Gap  6: 3:03.55 - 3:05.65 ( 2.1s - DELETED) → w nowym video: 3:03.55
    gap_pattern = r'Gap\s+(\d+):\s+(\d+):(\d+\.\d+)\s+-\s+(\d+):(\d+\.\d+)\s+\((\s*\d+\.\d+)s\s+-\s+DELETED\)'
    
    for line in gaps_text.strip().split('\n'):
        match = re.search(gap_pattern, line)
        if match:
            gap_id = int(match.group(1))
            start_min = int(match.group(2))
            start_sec = float(match.group(3))
            end_min = int(match.group(4))
            end_sec = float(match.group(5))
            duration = float(match.group(6))
            
            gap_start = start_min * 60 + start_sec
            gap_end = end_min * 60 + end_sec
            
            gaps_data.append({
                'gap_id': gap_id,
                'gap_start': gap_start,
                'gap_end': gap_end,
                'gap_duration': duration,
                'replacement_duration': 0.5,  # Domyślna wartość dla nowego formatu
                'static_ratio': 0.6  # Domyślna wartość dla nowego formatu
            })
            
            print(f"  Loaded Gap {gap_id}: {gap_start:.2f}s-{gap_end:.2f}s ({duration:.1f}s)")
    
    print(f"Loaded {len(gaps_data)} gaps from report")
    return gaps_data, {'original': original_video, 'processed': processed_video}

def parse_exclude_list(exclude_string):
    """Parse string like '5,12,18' into list of integers."""
    if not exclude_string:
        return []
    
    try:
        excluded = [int(x.strip()) for x in exclude_string.split(',')]
        print(f"Excluding gaps: {excluded}")
        return excluded
    except ValueError as e:
        print(f"Error parsing exclude list '{exclude_string}': {e}")
        return []

def filter_gaps(gaps_data, excluded_gap_ids):
    """Filtruje gaps - usuwa te które mają być wykluczone."""
    if not excluded_gap_ids:
        return gaps_data
    
    filtered_gaps = []
    excluded_count = 0
    
    for gap in gaps_data:
        if gap['gap_id'] in excluded_gap_ids:
            excluded_count += 1
            print(f"  Excluding Gap {gap['gap_id']}: {gap['gap_start']:.1f}s-{gap['gap_end']:.1f}s")
        else:
            filtered_gaps.append(gap)
    
    print(f"Filtered: {len(filtered_gaps)} gaps to process ({excluded_count} excluded)")
    return filtered_gaps

def compress_video_gaps(video_path, output_path, gaps_to_compress, replacement_duration=0.5):
    """Kompresuje gaps w video (skopiowane z delete_sm.py)."""
    video = VideoFileClip(video_path)
    clips = []
    current_time = 0
    
    print(f"\nReprocessing with {len(gaps_to_compress)} gaps...")
    
    # Sortuj gaps by gap_start
    gaps_sorted = sorted(gaps_to_compress, key=lambda x: x['gap_start'])
    
    for gap in tqdm(gaps_sorted, desc="Processing gaps"):
        gap_start = gap['gap_start']
        gap_end = gap['gap_end']
        gap_duration = gap['gap_duration']
        gap_id = gap['gap_id']
        
        # Dodaj normalną część przed przerwą
        if current_time < gap_start:
            normal_clip = video.subclip(current_time, gap_start)
            clips.append(normal_clip)
        
        # Zastąp przerwę krótkim freeze frame
        freeze_frame = video.get_frame(gap_start)
        freeze_clip = ImageClip(freeze_frame, duration=replacement_duration).set_fps(video.fps)
        clips.append(freeze_clip)
        
        print(f"  Compressed gap {gap_id}: {gap_start:.2f}s-{gap_end:.2f}s ({gap_duration:.2f}s) -> {replacement_duration:.2f}s")
        
        current_time = gap_end
    
    # Dodaj resztę filmu
    if current_time < video.duration:
        final_clip = video.subclip(current_time, video.duration)
        clips.append(final_clip)
    
    # Złącz wszystko
    print("Creating final video...")
    final_video = concatenate_videoclips(clips, method="compose")
    
    print(f"Writing to: {output_path}")
    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac", 
        fps=video.fps,
        verbose=False,
        logger=None
    )
    
    # Cleanup
    video.close()
    final_video.close()
    for clip in clips:
        if hasattr(clip, 'close'):
            clip.close()
    
    return len(gaps_to_compress)

def seconds_to_minsec_precise(seconds):
    """Konwertuje sekundy na format MM:SS.CC (z setnymi)."""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:06.2f}"

def generate_reprocess_report(original_gaps, processed_gaps, excluded_gaps, output_path, original_duration, replacement_duration, video_path):
    """Generuje raport reprocessingu."""
    report_path = Path(output_path).with_suffix('.txt').with_stem(Path(output_path).stem + '_reprocessed')
    
    total_gap_duration = sum(gap['gap_duration'] for gap in processed_gaps)
    total_replacement_duration = len(processed_gaps) * replacement_duration
    time_saved = total_gap_duration - total_replacement_duration
    new_duration = original_duration - time_saved
    
    excluded_time = sum(gap['gap_duration'] for gap in original_gaps if gap['gap_id'] in [g['gap_id'] for g in excluded_gaps])
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Raport reprocessingu - selective gap compression\n")
        f.write("==============================================\n\n")
        f.write(f"Plik źródłowy: {Path(video_path).name}\n")
        f.write(f"Plik wyjściowy: {Path(output_path).name}\n\n")
        
        f.write(f"Oryginalnie znalezionych gaps: {len(original_gaps)}\n")
        f.write(f"Wykluczonych gaps: {len(excluded_gaps)}\n")
        f.write(f"Przetworzonych gaps: {len(processed_gaps)}\n\n")
        
        if excluded_gaps:
            f.write("Wykluczone gaps (zachowane w oryginalnej formie):\n")
            f.write("-" * 60 + "\n")
            for gap in excluded_gaps:
                start_time = seconds_to_minsec_precise(gap['gap_start'])
                end_time = seconds_to_minsec_precise(gap['gap_end'])
                f.write(f"Gap {gap['gap_id']:>2}: {start_time} - {end_time} ({gap['gap_duration']:>4.1f}s) - ZACHOWANE\n")
            f.write("\n")
        
        f.write("Przetworzone gaps:\n")
        f.write("-" * 80 + "\n")
        
        # Oblicz timestampy w nowym video
        cumulative_time_saved = 0
        new_video_timestamps = []
        
        for gap in processed_gaps:
            start_time = seconds_to_minsec_precise(gap['gap_start'])
            end_time = seconds_to_minsec_precise(gap['gap_end'])
            gap_id = gap['gap_id']
            static_ratio = gap.get('static_ratio', 0)
            
            # Oblicz timestamp przejścia w nowym video
            new_video_timestamp = gap['gap_start'] - cumulative_time_saved
            new_video_time_str = seconds_to_minsec_precise(new_video_timestamp)
            new_video_timestamps.append(new_video_time_str)
            
            # Dodaj oszczędność czasu z tego gap'a
            time_saved_this_gap = gap['gap_duration'] - replacement_duration
            cumulative_time_saved += time_saved_this_gap
            
            f.write(f"Gap {gap_id:>2}: {start_time} - {end_time} ")
            f.write(f"({gap['gap_duration']:>4.1f}s -> {replacement_duration:.1f}s) ")
            f.write(f"[{static_ratio:.0%}] → w nowym video: {new_video_time_str}\n")
        
        # Podsumowanie
        f.write(f"\nOryginalny czas: {original_duration/60:.1f} min ({original_duration:.1f}s)\n")
        f.write(f"Nowy czas: {new_duration/60:.1f} min ({new_duration:.1f}s)\n")
        f.write(f"Zaoszczędzony czas: {time_saved/60:.1f} min ({time_saved:.1f}s)\n")
        f.write(f"Zachowany czas (wykluczone gaps): {excluded_time/60:.1f} min ({excluded_time:.1f}s)\n")
        f.write(f"Redukcja: {(time_saved/original_duration)*100:.1f}%\n\n")
        
        if new_video_timestamps:
            f.write(f"Sprawdź przejścia w NOWYM video: {', '.join(new_video_timestamps)}\n")
    
    print(f"Raport reprocessingu zapisany: {report_path}")
    
    # Wyświetl timestampy również w konsoli
    if new_video_timestamps:
        print(f"\n📍 Sprawdź przejścia w nowym video: {', '.join(new_video_timestamps)}")

def main():
    parser = argparse.ArgumentParser(description="Reprocess video with selective gap exclusion")
    parser.add_argument("original_video", help="Original video file (source)")
    parser.add_argument("output_video", help="Output video file")
    parser.add_argument("--report", help="Path to existing delete_sm.py report file")
    parser.add_argument("--exclude-gaps", help="Comma-separated list of gap IDs to exclude (e.g., '5,12,18')")
    parser.add_argument("--replacement-duration", type=float, default=0.5, help="Replacement duration (s)")
    
    args = parser.parse_args()
    
    print("🔄 Video Reprocessor - Selective Gap Compression")
    print(f"Original video: {args.original_video}")
    print(f"Output video: {args.output_video}")
    print("-" * 60)
    
    # Sprawdź pliki
    original_video_path = Path(args.original_video)
    if not original_video_path.exists():
        print(f"Error: Original video not found: {original_video_path}")
        return
    
    # Znajdź raport automatycznie jeśli nie podano
    if not args.report:
        # Szukaj raportu na podstawie nazwy output video
        output_video_path = Path(args.output_video)
        potential_report = output_video_path.with_suffix('.txt')
        if potential_report.exists():
            args.report = str(potential_report)
            print(f"Auto-detected report: {args.report}")
        else:
            print("Error: No report file specified and could not auto-detect")
            print("Use --report parameter to specify report file")
            return
    
    # Wczytaj dane z raportu
    gaps_data, file_info = parse_existing_report(args.report)
    if not gaps_data:
        return
    
    # Parse exclude list
    excluded_gap_ids = parse_exclude_list(args.exclude_gaps)
    
    # Filtruj gaps
    gaps_to_process = filter_gaps(gaps_data, excluded_gap_ids)
    excluded_gaps = [gap for gap in gaps_data if gap['gap_id'] in excluded_gap_ids]
    
    if not gaps_to_process:
        print("No gaps to process after exclusions!")
        return
    
    # Pobierz czas trwania oryginalnego video
    video = VideoFileClip(str(original_video_path))
    original_duration = video.duration
    video.close()
    print(f"Original video duration: {original_duration/60:.1f} minutes")
    
    # Przetwórz video
    compressed_count = compress_video_gaps(
        str(original_video_path),
        args.output_video,
        gaps_to_process,
        args.replacement_duration
    )
    
    # Generuj raport
    generate_reprocess_report(
        gaps_data, 
        gaps_to_process, 
        excluded_gaps,
        args.output_video, 
        original_duration, 
        args.replacement_duration, 
        str(original_video_path)
    )
    
    print(f"\n[SUKCES] Reprocessing completed!")
    print(f"Processed {compressed_count} gaps")
    print(f"Excluded {len(excluded_gaps)} gaps")
    print(f"Output: {args.output_video}")
    
    # Dźwięk zakończenia
    try:
        import winsound
        winsound.Beep(1000, 500)
    except ImportError:
        print("🔔 Process completed!")

if __name__ == "__main__":
    main()