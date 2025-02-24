import argparse
import cv2
import numpy as np
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from pydub import AudioSegment, silence
from pathlib import Path
from tqdm import tqdm
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import logging
import subprocess
from pathlib import Path
from tqdm import tqdm
import logging


# Konfiguracja loggera
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,  # Ustaw poziom logowania (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Format wiadomości logowania
)

# Tworzenie obiektu loggera
logger = logging.getLogger(__name__)

def detect_silent_segments(audio_path, min_silence_len=3000, silence_thresh=-40):
    audio = AudioSegment.from_file(audio_path)
    silent_segments = silence.detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
    return [(start / 1000, end / 1000) for start, end in silent_segments]

def detect_static_segments(video_path, threshold=30, min_static_duration=3):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    static_segments = []
    static_start = None
    prev_frame = None
    static_duration = 0

    # Używamy tqdm do wyświetlenia postępu
    for _ in tqdm(range(frame_count), desc="Analyzing frames for static segments"):
        ret, frame = cap.read()
        if not ret:
            break

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, frame_gray)
            non_static = np.sum(diff > threshold)

            if non_static < 10:
                static_duration += 1 / fps
                if static_start is None:
                    static_start = (cap.get(cv2.CAP_PROP_POS_FRAMES) - 1) / fps
            else:
                if static_start is not None and static_duration >= min_static_duration:
                    static_segments.append((static_start, static_start + static_duration))
                static_start = None
                static_duration = 0

        prev_frame = frame_gray

    cap.release()
    return static_segments

def merge_segments(silent_segments, static_segments, min_duration):
    merged_segments = []
    for s_start, s_end in silent_segments:
        for v_start, v_end in static_segments:
            overlap_start = max(s_start, v_start)
            overlap_end = min(s_end, v_end)
            if overlap_end - overlap_start >= min_duration:
                merged_segments.append((overlap_start, overlap_end))
    return merged_segments

def remove_segments(video_path, output_path, silent_segments, static_segments, min_duration, silence_padding=1.0):
    video = VideoFileClip(video_path)
    clips = []
    start = 0

    for s_start, s_end in tqdm(silent_segments, desc="Processing silent and static segments"):
        # Sprawdź, czy segment ciszy nakłada się na segment statyczny
        overlapping_static_segments = [
            (v_start, v_end)
            for v_start, v_end in static_segments
            if max(s_start, v_start) < min(s_end, v_end)
        ]

        if overlapping_static_segments:
            # Oblicz wspólny obszar ciszy i bezruchu
            for v_start, v_end in overlapping_static_segments:
                overlap_start = max(s_start, v_start)
                overlap_end = min(s_end, v_end)

                if overlap_end - overlap_start >= min_duration:
                    # Jeśli segment spełnia oba warunki, usuń go
                    logger.info(f"Removing segment: {overlap_start:.2f}s - {overlap_end:.2f}s")
                    if start < overlap_start:
                        # Dodaj część przed segmentem do listy klipów
                        clips.append(video.subclip(start, overlap_start))
                    start = overlap_end

        else:
            # Jeśli segment nie spełnia obu warunków, zachowaj wideo
            if start < s_start:
                clips.append(video.subclip(start, s_start))
                # Dodaj ciszę w postaci stop-klatki
                freeze_frame = video.get_frame(s_start)
                freeze_clip = ImageClip(freeze_frame).set_duration(silence_padding).set_fps(video.fps)
                clips.append(freeze_clip)

        start = max(start, s_end)

    # Dodanie końcowego segmentu, jeśli istnieje
    if start < video.duration:
        clips.append(video.subclip(start, video.duration))

    # Łączenie segmentów w jeden klip
    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(output_path, codec="libx264", fps=video.fps)

    video.close()
  
def seconds_to_minsec(seconds):
    """Konwertuje sekundy na format MM:SS."""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:05.2f}"

def generate_report(segments, output_path, original_duration, silence_padding, video_path):
    """Generate detailed report with padding time consideration."""
    report_path = Path(output_path).with_suffix('.txt')
    
    # Obliczenia czasu
    total_silence = sum(end - start for start, end in segments)
    total_padding = len(segments) * silence_padding
    actual_duration = original_duration - total_silence + total_padding
    
    with open(report_path, "w", encoding="utf-8") as report_file:
        # Nagłówek raportu
        report_file.write("Raport usuwania fragmentów ciszy\n")
        report_file.write("===============================\n\n")
        report_file.write(f"Plik wejściowy: {Path(video_path).name}\n")
        report_file.write(f"Plik wyjściowy: {Path(output_path).name}\n")
        report_file.write(f"Długość przejścia (padding): {silence_padding:.1f}s\n\n")
        
        # Podsumowanie
        report_file.write(f"Liczba usuniętych segmentów: {len(segments)}\n")
        report_file.write(f"Całkowity czas usuniętej ciszy: {seconds_to_minsec(total_silence)} ({total_silence:.2f}s)\n")
        report_file.write(f"Całkowity czas dodanych przejść: {seconds_to_minsec(total_padding)} ({total_padding:.2f}s)\n")
        report_file.write(f"Oryginalny czas trwania: {seconds_to_minsec(original_duration)} ({original_duration:.2f}s)\n")
        report_file.write(f"Faktyczny czas po edycji: {seconds_to_minsec(actual_duration)} ({actual_duration:.2f}s)\n")
        report_file.write(f"Rzeczywista redukcja czasu: {((original_duration - actual_duration) / original_duration) * 100:.1f}%\n\n")
        
        # Szczegóły usuniętych segmentów
        report_file.write("Szczegóły usuniętych segmentów:\n")
        report_file.write("-----------------------------\n")
        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            report_file.write(
                f"Segment {i:>3}: {seconds_to_minsec(start)} -> {seconds_to_minsec(end)} "
                f"(długość: {seconds_to_minsec(duration)})\n"
            )
    
    print(f"Raport został zapisany do: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Remove silent and static segments from video.")
    parser.add_argument("video_file", help="Path to the input video file")
    parser.add_argument("output_file", help="Path to the output video file")
    parser.add_argument("--audio_file", help="Path to the audio file (optional)")
    parser.add_argument("--min_silence_len", type=int, default=3000, help="Minimum length of silence to detect (ms)")
    parser.add_argument("--silence_thresh", type=int, default=-40, help="Threshold for silence detection (dB)")
    parser.add_argument("--static_threshold", type=int, default=30, help="Threshold for detecting static frames")
    parser.add_argument("--min_static_duration", type=int, default=3, help="Minimum duration of static frames (s)")
    parser.add_argument("--min_duration", type=float, default=3, help="Minimum overlap duration of silence and static frames (s)")
    args = parser.parse_args()

    # Ustal ścieżkę do pliku audio lub wyodrębnij ją z wideo
    audio_path = args.audio_file
    if not audio_path:
        audio_path = "temp_audio.wav"
        video = VideoFileClip(args.video_file)
        print(type(video))  # Sprawdzamy typ obiektu
        print("Extracting audio...")
        video.audio.write_audiofile(audio_path)

    # Wykryj ciszę
    print("Detecting silent segments...")
    silent_segments = detect_silent_segments(audio_path, args.min_silence_len, args.silence_thresh)

    # Wykryj statyczne segmenty
    print("Detecting static segments in video...")
    static_segments = detect_static_segments(args.video_file, args.static_threshold, args.min_static_duration)

    # Połącz segmenty ciszy i statyczności
    print("Merging silent and static segments...")
    segments_to_remove = merge_segments(silent_segments, static_segments, args.min_duration)

    # Usuń wybrane segmenty z wideo
    print("Removing detected segments and creating output video...")
    remove_segments(args.video_file, args.output_file, silent_segments, static_segments, args.min_duration, silence_padding=1.0)

     # Generowanie raportu
    generate_report(segments_to_remove, args.output_file, original_duration=video.duration, silence_padding=1.0, video_path=args.video_file)

    # Usuń tymczasowy plik audio, jeśli został utworzony
    if not args.audio_file:
        Path(audio_path).unlink()

# Dodaj dźwięk zakończenia
    import winsound
    winsound.Beep(1000, 500)  # Sygnał o częstotliwości 1000Hz trwający 500ms

if __name__ == "__main__":
    main()