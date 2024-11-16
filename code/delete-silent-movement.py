import argparse
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips
from pydub import AudioSegment, silence
from pathlib import Path
from tqdm import tqdm

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

def merge_segments(silent_segments, static_segments, min_duration=3):
    merged_segments = []
    for s_start, s_end in silent_segments:
        for v_start, v_end in static_segments:
            overlap_start = max(s_start, v_start)
            overlap_end = min(s_end, v_end)
            if overlap_end - overlap_start >= min_duration:
                merged_segments.append((overlap_start, overlap_end))
    return merged_segments

def remove_segments(video_path, output_path, segments):
    video = VideoFileClip(video_path)
    clips = []
    start = 0

    # Używamy tqdm do wyświetlenia postępu przy łączeniu segmentów
    for s_start, s_end in tqdm(segments, desc="Removing silent/static segments"):
        if start < s_start:
            clips.append(video.subclip(start, s_start))
        start = s_end
    if start < video.duration:
        clips.append(video.subclip(start, video.duration))

    final_video = concatenate_videoclips(clips)
    final_video.write_videofile(output_path, codec="libx264")

def generate_report(segments, report_path):
    with open(report_path, "w") as report_file:
        report_file.write("Report of Removed Segments\n")
        report_file.write("==========================\n")
        report_file.write(f"Total segments removed: {len(segments)}\n\n")
        report_file.write("Details of each segment:\n")
        
        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            report_file.write(f"Segment {i}: Start = {start:.2f}s, End = {end:.2f}s, Duration = {duration:.2f}s\n")

    print(f"\nReport generated: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Remove silent and static segments from video.")
    parser.add_argument("video_file", help="Path to the input video file")
    parser.add_argument("output_file", help="Path to the output video file")
    parser.add_argument("--audio_file", help="Path to the audio file (optional)")
    parser.add_argument("--min_silence_len", type=int, default=3000, help="Minimum length of silence to detect (ms)")
    parser.add_argument("--silence_thresh", type=int, default=-40, help="Threshold for silence detection (dB)")
    parser.add_argument("--static_threshold", type=int, default=30, help="Threshold for detecting static frames")
    parser.add_argument("--min_static_duration", type=float, default=3, help="Minimum duration of static frames (s)")
    parser.add_argument("--report_file", default="removal_report.txt", help="Path to save the report file")
    args = parser.parse_args()

    # Ustal ścieżkę do pliku audio lub wyodrębnij ją z wideo
    audio_path = args.audio_file
    if not audio_path:
        audio_path = "temp_audio.wav"
        video = VideoFileClip(args.video_file)
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
    segments_to_remove = merge_segments(silent_segments, static_segments)

    # Usuń wybrane segmenty z wideo
    print("Removing detected segments and creating output video...")
    remove_segments(args.video_file, args.output_file, segments_to_remove)

     # Generowanie raportu
    generate_report(segments_to_remove, args.report_file)

    # Usuń tymczasowy plik audio, jeśli został utworzony
    if not args.audio_file:
        Path(audio_path).unlink()

if __name__ == "__main__":
    main()