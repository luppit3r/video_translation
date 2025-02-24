import argparse
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from pydub import AudioSegment, silence
from pathlib import Path
from tqdm import tqdm
from moviepy.video.VideoClip import ImageClip
import winsound

# Funkcja wykrywania ciszy
def detect_silent_segments(audio_path, min_silence_len=3000, silence_thresh=-40):
<<<<<<< Updated upstream
=======
    """Detect silent segments in the audio file."""
>>>>>>> Stashed changes
    audio = AudioSegment.from_file(audio_path)
    silent_segments = silence.detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
    return [(start / 1000, end / 1000) for start, end in silent_segments]

# Funkcja usuwania segmentów
def remove_segments(video_path, output_path, silent_segments, silence_padding=1.0):
    video = VideoFileClip(video_path)
    clips = []
    start = 0

    for s_start, s_end in tqdm(silent_segments, desc="Processing silent segments"):
        if start < s_start:
            clip = video.subclip(start, s_start)
            clips.append(clip)

            # Dodanie stop-klatki
            freeze_frame = video.get_frame(s_start)
            freeze_clip = ImageClip(freeze_frame).set_duration(silence_padding).set_fps(video.fps)
            clips.append(freeze_clip)

        start = s_end

    if start < video.duration:
        clips.append(video.subclip(start, video.duration))

    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(output_path, codec="libx264", fps=video.fps)

    video.close()

# Funkcja konwersji czasu
def seconds_to_minsec(seconds):
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:05.2f}"

# Funkcja generowania raportu
def generate_report(segments, output_path, original_duration, silence_padding, video_path):
    report_path = Path(output_path).with_suffix('.txt')
    
    total_silence = sum(end - start for start, end in segments)
    total_padding = len(segments) * silence_padding
    actual_duration = original_duration - total_silence + total_padding

    with open(report_path, "w", encoding="utf-8") as report_file:
        report_file.write("Raport usuwania fragmentów ciszy\n")
        report_file.write("===============================\n\n")
        report_file.write(f"Plik wejściowy: {Path(video_path).name}\n")
        report_file.write(f"Plik wyjściowy: {Path(output_path).name}\n")
        report_file.write(f"Długość przejścia (padding): {silence_padding:.1f}s\n\n")
        report_file.write(f"Liczba usuniętych segmentów: {len(segments)}\n")
        report_file.write(f"Całkowity czas usuniętej ciszy: {seconds_to_minsec(total_silence)} ({total_silence:.2f}s)\n")
        report_file.write(f"Całkowity czas dodanych przejść: {seconds_to_minsec(total_padding)} ({total_padding:.2f}s)\n")
        report_file.write(f"Oryginalny czas trwania: {seconds_to_minsec(original_duration)} ({original_duration:.2f}s)\n")
        report_file.write(f"Faktyczny czas po edycji: {seconds_to_minsec(actual_duration)} ({actual_duration:.2f}s)\n")
        report_file.write(f"Rzeczywista redukcja czasu: {((original_duration - actual_duration) / original_duration) * 100:.1f}%\n\n")
        report_file.write("Szczegóły usuniętych segmentów:\n")
        report_file.write("-----------------------------\n")
        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            report_file.write(
                f"Segment {i:>3}: {seconds_to_minsec(start)} -> {seconds_to_minsec(end)} "
                f"(długość: {seconds_to_minsec(duration)})\n"
            )

    print(f"Raport został zapisany do: {report_path}")

# Główna funkcja
def main():
    parser = argparse.ArgumentParser(description="Remove silent segments from video.")
    parser.add_argument("video_file", help="Path to the input video file")
    parser.add_argument("output_file", help="Path to the output video file")
    parser.add_argument("--audio_file", help="Path to the audio file (optional)")
    parser.add_argument("--min_silence_len", type=int, default=3000, help="Minimum length of silence to detect (ms)")
    parser.add_argument("--silence_thresh", type=int, default=-40, help="Threshold for silence detection (dB)")
    args = parser.parse_args()

    audio_path = args.audio_file
    if not audio_path:
        audio_path = "temp_audio.wav"
        video = VideoFileClip(args.video_file)
        print(type(video))
        print("Extracting audio...")
        video.audio.write_audiofile(audio_path)

    print("Detecting silent segments...")
    silent_segments = detect_silent_segments(audio_path, args.min_silence_len, args.silence_thresh)

    print("Removing detected segments and creating output video...")
    remove_segments(args.video_file, args.output_file, silent_segments, silence_padding=1.0)

    print("Generating report...")
    generate_report(silent_segments, args.output_file, original_duration=video.duration, silence_padding=1.0, video_path=args.video_file)

    if not args.audio_file:
        Path(audio_path).unlink()
=======
def generate_report(segments, output_video_path, original_duration):
    """Generate detailed report of removed segments in the same directory as output video."""
    # Generuj ścieżkę raportu w tym samym katalogu co wideo
    report_path = Path(output_video_path).with_suffix('.txt')
    
    total_silence = sum(end - start for start, end in segments)
    
    with open(report_path, "w", encoding="utf-8") as report_file:
        report_file.write("Raport usuwania fragmentów ciszy\n")
        report_file.write("===============================\n\n")
        report_file.write(f"Plik wideo: {Path(output_video_path).name}\n\n")
        report_file.write(f"Liczba usuniętych segmentów: {len(segments)}\n")
        report_file.write(f"Całkowity czas usuniętej ciszy: {total_silence:.2f}s\n")
        report_file.write(f"Oryginalny czas trwania: {original_duration:.2f}s\n")
        report_file.write(f"Szacowany czas po edycji: {(original_duration - total_silence):.2f}s\n")
        report_file.write(f"Redukcja czasu: {(total_silence/original_duration)*100:.1f}%\n\n")
        
        report_file.write("Szczegóły usuniętych segmentów:\n")
        report_file.write("-----------------------------\n")
        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            report_file.write(f"Segment {i:3d}: {start:8.2f}s - {end:8.2f}s (długość: {duration:6.2f}s)\n")
    
    print(f"\nRaport zapisano w: {report_path}")

def process_video(video_path, output_path, segments, silence_padding=0.5):
    """Process video at original resolution with good performance."""
    video = VideoFileClip(video_path, audio=True)
    original_duration = video.duration
    clips = []
    current_time = 0
    
    try:
        for s_start, s_end in tqdm(segments, desc="Przetwarzanie segmentów"):
            if current_time < s_start:
                clip = video.subclip(current_time, s_start)
                
                if silence_padding > 0:
                    clip = clip.set_duration(clip.duration + silence_padding)
                
                clips.append(clip)
            current_time = s_end

        # Add remaining video after last silent segment
        if current_time < video.duration:
            clips.append(video.subclip(current_time, video.duration))

        print("Łączenie segmentów...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        print("Zapisywanie pliku wyjściowego...")
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            preset="faster",
            threads=8,
            fps=video.fps,
            verbose=False
        )
        
        # Generate report after successful video processing
        generate_report(segments, output_path, original_duration)
        
    except Exception as e:
        print(f"Błąd podczas przetwarzania: {str(e)}")
        raise
        
    finally:
        video.close()
        for clip in clips:
            try:
                clip.close()
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description="Usuń fragmenty ciszy z wideo.")
    parser.add_argument("video_file", help="Ścieżka do pliku wejściowego")
    parser.add_argument("output_file", help="Ścieżka do pliku wyjściowego")
    parser.add_argument("--min_silence_len", type=int, default=3000,
                        help="Minimalna długość wykrywanej ciszy (ms)")
    parser.add_argument("--silence_thresh", type=int, default=-40,
                        help="Próg wykrywania ciszy (dB)")
    parser.add_argument("--silence_padding", type=float, default=0.5,
                        help="Długość przejścia w miejscu ciszy (s)")
    args = parser.parse_args()

    audio_path = "temp_audio.wav"
    try:
        print("Wyodrębnianie ścieżki audio...")
        video = VideoFileClip(args.video_file, audio=True)
        video.audio.write_audiofile(audio_path, verbose=False)
        video.close()
        
        print("Wykrywanie fragmentów ciszy...")
        silent_segments = detect_silent_segments(
            audio_path,
            args.min_silence_len,
            args.silence_thresh
        )
        
        process_video(
            args.video_file,
            args.output_file,
            silent_segments,
            args.silence_padding
        )
        
        print("Zakończono przetwarzanie!")
        
    except Exception as e:
        print(f"Wystąpił błąd: {str(e)}")
        
    finally:
        if Path(audio_path).exists():
            Path(audio_path).unlink()
>>>>>>> Stashed changes

    winsound.Beep(1000, 500)

if __name__ == "__main__":
    main()