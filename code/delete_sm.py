import argparse
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips, ImageClip, AudioFileClip
from pydub import AudioSegment, silence
from pathlib import Path
from tqdm import tqdm

def detect_silent_segments(video_path, min_silence_len=2000, silence_thresh=-40, gap_margin=0.5):
    """Wykrywa segmenty ciszy w audio z video z marginesem bezpieczeństwa."""
    print("Extracting audio for silence detection...")
    
    # Wyciągnij audio z video
    video = VideoFileClip(video_path)
    audio_path = "temp_silence_detection.wav"
    video.audio.write_audiofile(audio_path, verbose=False, logger=None)
    video.close()
    
    print("Detecting silent segments...")
    audio = AudioSegment.from_file(audio_path)
    silent_segments = silence.detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
    
    # Cleanup
    Path(audio_path).unlink()
    
    gaps = []
    for i, (start, end) in enumerate(silent_segments):
        # Oryginalne wykrycie ciszy
        original_start = start / 1000  # Convert to seconds
        original_end = end / 1000
        original_duration = original_end - original_start
        
        # Dodaj margines bezpieczeństwa (0.5s na początku i końcu)
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
            
            print(f"Silent gap {i+1}: {original_start:.2f}s to {original_end:.2f}s ({original_duration:.2f}s)")
            print(f"  -> Adjusted gap: {gap_start:.2f}s to {gap_end:.2f}s ({gap_duration:.2f}s) [margin: ±{gap_margin}s]")
        else:
            print(f"Silent gap {i+1}: {original_start:.2f}s to {original_end:.2f}s ({original_duration:.2f}s) - too short after margin adjustment")
    
    print(f"Found {len(gaps)} silent segments >= {min_silence_len/1000}s (with {gap_margin}s margin)")
    return gaps

def check_movement_in_gaps(video_path, gaps, movement_threshold=20, min_static_pixels=300, debug_mode=False):
    """Sprawdza ruch w gap'ach ciszy z algorytmem dominacji bezruchu."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    gaps_to_compress = []
    DOMINANCE_THRESHOLD = 0.6  # 60% bezruch = kompresuj cały gap
    
    for gap in tqdm(gaps, desc="Analyzing movement in silent gaps"):
        gap_start = gap['gap_start']
        gap_end = gap['gap_end']
        gap_duration = gap['gap_duration']
        gap_id = gap['gap_id']
        
        print(f"\n  Gap {gap_id}: {gap_start:.1f}s-{gap_end:.1f}s ({gap_duration:.1f}s)")
        
        # Precyzyjna analiza - sprawdzaj co sekundę
        analysis_step = 1.0  # Co sekundę
        movement_timeline = []
        
        current_time = gap_start
        while current_time < gap_end:
            check_end = min(current_time + analysis_step, gap_end)
            
            # Sprawdź ruch w tym 1s segmencie
            start_frame = int(current_time * fps)
            end_frame = int(check_end * fps)
            
            has_movement = False
            max_movement_pixels = 0
            frame_with_max_movement = 0
            prev_frame = None
            frames_checked = 0
            
            # Sprawdź więcej klatek w tym segmencie dla lepszej precyzji
            frame_step = max(1, (end_frame - start_frame) // 5)  # 5 sprawdzeń na sekundę
            
            for frame_num in range(start_frame, end_frame, frame_step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if not ret:
                    break
                    
                frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frames_checked += 1
                
                if prev_frame is not None:
                    diff = cv2.absdiff(prev_frame, frame_gray)
                    movement_pixels = np.sum(diff > movement_threshold)
                    
                    if movement_pixels > max_movement_pixels:
                        max_movement_pixels = movement_pixels
                        frame_with_max_movement = frame_num
                    
                    if movement_pixels > min_static_pixels:
                        has_movement = True
                        if debug_mode:
                            frame_time = frame_num / fps
                            print(f"      [DEBUG] Frame {frame_num} ({frame_time:.2f}s): {movement_pixels} changed pixels > {min_static_pixels} threshold")
                
                prev_frame = frame_gray
            
            segment_duration = check_end - current_time
            movement_timeline.append({
                'start': current_time,
                'end': check_end,
                'duration': segment_duration,
                'has_movement': has_movement,
                'max_movement_pixels': max_movement_pixels,
                'frame_with_max_movement': frame_with_max_movement,
                'frames_checked': frames_checked
            })
            
            current_time = check_end
        
        # Oblicz dominację bezruchu
        total_duration = sum(seg['duration'] for seg in movement_timeline)
        static_duration = sum(seg['duration'] for seg in movement_timeline if not seg['has_movement'])
        static_ratio = static_duration / total_duration if total_duration > 0 else 0
        
        # Wyświetl analizę
        if debug_mode:
            print(f"    [DEBUG] Movement analysis (threshold: {movement_threshold}, min_pixels: {min_static_pixels}):")
        else:
            print(f"    Movement timeline:")
            
        for segment in movement_timeline:
            seg_start = segment['start']
            seg_end = segment['end']
            has_movement = segment['has_movement']
            max_pixels = segment['max_movement_pixels']
            max_frame = segment['frame_with_max_movement']
            frames_checked = segment['frames_checked']
            
            if debug_mode:
                status = "[RUCH]" if has_movement else "[bezruch]"
                frame_time = max_frame / fps if max_frame > 0 else 0
                print(f"      {seg_start:>5.1f}s-{seg_end:>5.1f}s: {status:>10} | max: {max_pixels:>4} pixels @ {frame_time:>6.2f}s | frames: {frames_checked}")
            else:
                status = "RUCH" if has_movement else "bezruch"
                print(f"      {seg_start:.1f}s-{seg_end:.1f}s: {status}")
        
        # Decyzja na podstawie dominacji
        print(f"    [ANALIZA] Analiza dominacji: {static_duration:.1f}s bezruch / {total_duration:.1f}s total = {static_ratio:.1%}")
        
        if static_ratio >= DOMINANCE_THRESHOLD:
            # Bezruch dominuje - kompresuj cały gap
            gaps_to_compress.append({
                'gap_id': gap_id,
                'gap_start': gap_start,
                'gap_end': gap_end,
                'gap_duration': gap_duration,
                'static_ratio': static_ratio,
                'compression_type': 'full_gap'
            })
            print(f"    [OK] KOMPRESUJ CAŁY GAP: Bezruch dominuje ({static_ratio:.1%} >= {DOMINANCE_THRESHOLD:.1%})")
        else:
            # Ruch dominuje - zachowaj cały gap
            print(f"    [BLAD] ZACHOWAJ GAP: Ruch dominuje ({static_ratio:.1%} < {DOMINANCE_THRESHOLD:.1%})")
    
    cap.release()
    print(f"\n[PODSUMOWANIE] Summary: Found {len(gaps_to_compress)} gaps to compress based on {DOMINANCE_THRESHOLD:.0%} dominance rule")
    return gaps_to_compress

def compress_video_gaps(video_path, output_path, gaps_to_compress, replacement_duration=1.0):
    """Usuwa gaps z video (bez zastępowania freeze frame'ami)."""
    video = VideoFileClip(video_path)
    clips = []
    current_time = 0
    
    print(f"\nRemoving {len(gaps_to_compress)} gaps...")
    
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
        
        # POMIŃ gap - nie dodawaj żadnego freeze frame'a
        # Po prostu przejdź do następnej części
        
        print(f"  Removed gap {gap_id}: {gap_start:.2f}s-{gap_end:.2f}s ({gap_duration:.2f}s) - DELETED")
        
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
    return f"{minutes}:{remaining_seconds:05.2f}"

def generate_report(all_gaps, gaps_compressed, output_path, original_duration, replacement_duration, video_path):
    """Generuje raport kompresji."""
    if not gaps_compressed:
        print("No gaps compressed - skipping report generation")
        return
        
    report_path = Path(output_path).with_suffix('.txt')
    
    total_gap_duration = sum(gap['gap_duration'] for gap in gaps_compressed)
    time_saved = total_gap_duration  # Cały czas gap'a jest oszczędzony
    new_duration = original_duration - time_saved
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Raport kompresji fragmentów ciszy\n")
        f.write("=================================\n\n")
        f.write(f"Plik wejściowy: {Path(video_path).name}\n")
        f.write(f"Plik wyjściowy: {Path(output_path).name}\n\n")
        
        f.write(f"Fragmenty ciszy znalezione: {len(all_gaps)}\n")
        f.write(f"Fragmenty z ruchem (pominięte): {len(all_gaps) - len(gaps_compressed)}\n") 
        f.write(f"Fragmenty skompresowane: {len(gaps_compressed)}\n\n")
        
        f.write(f"Oryginalny czas: {original_duration/60:.1f} min ({original_duration:.1f}s)\n")
        f.write(f"Nowy czas: {new_duration/60:.1f} min ({new_duration:.1f}s)\n")
        f.write(f"Zaoszczędzony czas: {time_saved/60:.1f} min ({time_saved:.1f}s)\n")
        f.write(f"Redukcja: {(time_saved/original_duration)*100:.1f}%\n\n")
        
        f.write("Usunięte gaps (60% dominacja bezruchu):\n")
        f.write("-" * 80 + "\n")
        
        # Oblicz timestampy w nowym video
        cumulative_time_saved = 0
        new_video_timestamps = []
        
        for gap in gaps_compressed:
            start_time = seconds_to_minsec_precise(gap['gap_start'])
            end_time = seconds_to_minsec_precise(gap['gap_end'])
            gap_id = gap.get('gap_id', '?')
            static_ratio = gap.get('static_ratio', 0)
            
            # Oblicz timestamp przejścia w nowym video
            # Miejsce gdzie zaczyna się padding w nowym video
            new_video_timestamp = gap['gap_start'] - cumulative_time_saved
            new_video_time_str = seconds_to_minsec_precise(new_video_timestamp)
            new_video_timestamps.append(new_video_time_str)
            
            # Dodaj oszczędność czasu z tego gap'a
            time_saved_this_gap = gap['gap_duration']  # Cały gap jest usunięty
            cumulative_time_saved += time_saved_this_gap
            
            f.write(f"Gap {gap_id:>2}: {start_time} - {end_time} ")
            f.write(f"({gap['gap_duration']:>4.1f}s - DELETED) ")
            f.write(f"-> w nowym video: {new_video_time_str}\n")
        
        # Podsumowanie timestampów
        f.write(f"\nSprawdź przejścia w NOWYM video: {', '.join(new_video_timestamps)}\n")
        
        # Instrukcje cofnięcia
        f.write(f"\nInstrukcje cofnięcia usunięć:\n")
        f.write("-" * 40 + "\n")
        f.write("Jeśli któreś wycięcie było błędne, możesz je cofnąć:\n\n")
        
        script_name = Path(video_path).stem + "_reprocess.py"  # Tymczasowo
        
        for gap in gaps_compressed:
            gap_id = gap.get('gap_id', '?')
            f.write(f"Cofnij Gap {gap_id}: python reprocess_delete_sm.py \"{Path(video_path).name}\" \"{Path(output_path).name}\" --exclude-gaps {gap_id}\n")
        
        f.write(f"\nCofnij kilka gaps: python reprocess_delete_sm.py \"{Path(video_path).name}\" \"{Path(output_path).name}\" --exclude-gaps 5,12,18\n")
        f.write(f"\n(Skrypt reprocess_delete_sm.py jest gotowy do użycia)\n")
    
    print(f"Raport zapisany: {report_path}")
    
    # Wyświetl timestampy również w konsoli
    if new_video_timestamps:
        print(f"\n[SPRAWDZ] Sprawdź przejścia w nowym video: {', '.join(new_video_timestamps)}")

def main():
    parser = argparse.ArgumentParser(description="Silence-based gap detection and compression")
    parser.add_argument("video_file", help="Input video file")
    parser.add_argument("output_file", help="Output video file (ignored if --report-only)")
    parser.add_argument("--min_silence_len", type=int, default=2000, help="Minimum silence length (ms)")
    parser.add_argument("--silence_thresh", type=int, default=-40, help="Silence detection threshold (dB)")
    parser.add_argument("--gap_margin", type=float, default=0.5, help="Safety margin around detected silence (s)")
    parser.add_argument("--replacement_duration", type=float, default=0.5, help="Replacement duration (s)")
    parser.add_argument("--movement_threshold", type=int, default=15, help="Movement detection threshold")
    parser.add_argument("--min_static_pixels", type=int, default=100, help="Min pixels to consider movement")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with detailed movement analysis")
    parser.add_argument("--report-only", action="store_true", help="Generate report only, don't create video")
    
    args = parser.parse_args()
    
    mode = "REPORT ONLY" if args.report_only else "FULL PROCESSING"
    print(f"Silence-based gap detection - {mode}")
    print(f"Video: {args.video_file}")
    if not args.report_only:
        print(f"Output: {args.output_file}")
    print(f"Min silence: {args.min_silence_len}ms, Threshold: {args.silence_thresh}dB")
    print(f"Gap margin: {args.gap_margin}s")
    print("-" * 60)
    
    # Sprawdź plik
    video_path = Path(args.video_file)
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}")
        return
    
    # Pobierz czas trwania
    video = VideoFileClip(str(video_path))
    original_duration = video.duration
    video.close()
    print(f"Video duration: {original_duration/60:.1f} minutes\n")
    
    # 1. Znajdź fragmenty ciszy
    silent_gaps = detect_silent_segments(
        str(video_path), 
        min_silence_len=args.min_silence_len,
        silence_thresh=args.silence_thresh,
        gap_margin=args.gap_margin
    )
    
    if not silent_gaps:
        print("No silent segments found!")
        return
    
    # 2. Sprawdź ruch w fragmentach ciszy
    gaps_to_compress = check_movement_in_gaps(
        str(video_path), 
        silent_gaps,
        args.movement_threshold,
        args.min_static_pixels,
        args.debug
    )
    
    # 3. Generuj raport
    if args.report_only:
        print(f"\n[RAPORT] REPORT ONLY MODE - Skipping video creation")
        report_path = Path(args.output_file).with_suffix('.txt') if args.output_file else Path("silence_analysis_report.txt") 
        generate_report(silent_gaps, gaps_to_compress, str(report_path), original_duration, args.replacement_duration, str(video_path))
        print(f"[OK] Report generated: {report_path}")
        return
    
    # 4. Kompresja video
    if not gaps_to_compress:
        print("All silent segments have movement - nothing to compress!")
        return
    
    compressed_count = compress_video_gaps(
        str(video_path),
        args.output_file,
        gaps_to_compress, 
        args.replacement_duration
    )
    
    # 5. Raport
    generate_report(silent_gaps, gaps_to_compress, args.output_file, original_duration, args.replacement_duration, str(video_path))
    
    print(f"\n[SUKCES] Success! Compressed {compressed_count} gaps")
    print(f"Output: {args.output_file}")
    
    # Dźwięk zakończenia
    try:
        import winsound
        winsound.Beep(1000, 500)
    except ImportError:
        print("[DZWONEK] Process completed!")

if __name__ == "__main__":
    main()