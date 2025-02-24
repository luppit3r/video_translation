import argparse
import cv2
import numpy as np
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio
from pydub import AudioSegment, silence
from pathlib import Path
from tqdm import tqdm
import os
import tempfile

def seconds_to_minsec(seconds):
    """Konwertuje sekundy na format MM:SS."""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:05.2f}"

def detect_silent_segments(audio_path, min_silence_len=3000, silence_thresh=-40):
    """Detect silent segments in the audio file."""
    audio = AudioSegment.from_file(audio_path)
    silent_segments = silence.detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
    return [(start / 1000, end / 1000) for start, end in silent_segments]

def generate_report(segments, output_path, original_duration, silence_padding, video_path):
    """Generate detailed report with padding time consideration."""
    report_path = Path(output_path).with_suffix('.txt')
    
    # Obliczenia z uwzględnieniem padding
    total_silence = sum(end - start for start, end in segments)
    total_padding = len(segments) * silence_padding
    actual_duration = original_duration - total_silence + total_padding
    
    with open(report_path, "w", encoding="utf-8") as report_file:
        report_file.write("Raport usuwania fragmentów ciszy\n")
        report_file.write("===============================\n\n")
        report_file.write(f"Plik wejściowy: {Path(video_path).name}\n")
        report_file.write(f"Plik wyjściowy: {Path(output_path).name}\n")
        report_file.write(f"Długość przejścia (padding): {silence_padding}s\n\n")
        
        report_file.write(f"Liczba usuniętych segmentów: {len(segments)}\n")
        report_file.write(f"Całkowity czas usuniętej ciszy: {seconds_to_minsec(total_silence)} ({total_silence:.2f}s)\n")
        report_file.write(f"Całkowity czas dodanych przejść: {seconds_to_minsec(total_padding)} ({total_padding:.2f}s)\n")
        report_file.write(f"Oryginalny czas trwania: {seconds_to_minsec(original_duration)} ({original_duration:.2f}s)\n")
        report_file.write(f"Faktyczny czas po edycji: {seconds_to_minsec(actual_duration)} ({actual_duration:.2f}s)\n")
        report_file.write(f"Rzeczywista redukcja czasu: {((original_duration - actual_duration)/original_duration)*100:.1f}%\n\n")
        
        report_file.write("Szczegóły usuniętych segmentów:\n")
        report_file.write("-----------------------------\n")
        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            report_file.write(
                f"Segment {i:3d}: "
                f"{seconds_to_minsec(start)} -> {seconds_to_minsec(end)} "
                f"(długość: {seconds_to_minsec(duration)})\n"
            )

def process_video(video_path, output_path, segments, silence_padding=0.5):
    """Process video at original resolution with improved error handling."""
    try:
        # Spróbuj otworzyć wideo z różnymi ustawieniami
        try:
            video = VideoFileClip(video_path, audio=True)
        except:
            # Jeśli nie zadziała, spróbuj z innymi parametrami
            video = VideoFileClip(video_path, audio=True, fps_source='tbr')
        
        original_duration = video.duration
        clips = []
        current_time = 0
        
        for s_start, s_end in tqdm(segments, desc="Przetwarzanie segmentów"):
            if current_time < s_start:
                try:
                    clip = video.subclip(current_time, s_start)
                    
                    if silence_padding > 0:
                        clip = clip.set_duration(clip.duration + silence_padding)
                    
                    clips.append(clip)
                except Exception as e:
                    print(f"Błąd podczas wycinania segmentu {current_time}-{s_start}: {str(e)}")
                    # Kontynuuj z następnym segmentem
                    
            current_time = s_end

        # Add remaining video after last silent segment
        if current_time < video.duration:
            try:
                clips.append(video.subclip(current_time, video.duration))
            except Exception as e:
                print(f"Błąd podczas wycinania ostatniego segmentu: {str(e)}")

        if not clips:
            raise ValueError("Nie udało się przetworzyć żadnego segmentu wideo!")

        print("Łączenie segmentów...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        print("Zapisywanie pliku wyjściowego...")
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            fps=video.fps,
            verbose=False
        )
        
        # Generate report
        generate_report(segments, output_path, original_duration, silence_padding, video_path)
        
    except Exception as e:
        print(f"Błąd podczas przetwarzania: {str(e)}")
        raise
        
    finally:
        try:
            video.close()
        except:
            pass
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

    temp_audio = tempfile.mktemp(suffix='.wav')
    try:
        print("Wyodrębnianie ścieżki audio...")
        try:
            # Najpierw spróbuj użyć ffmpeg_extract_audio
            ffmpeg_extract_audio(args.video_file, temp_audio)
        except:
            # Jeśli nie zadziała, użyj VideoFileClip
            video = VideoFileClip(args.video_file, audio=True)
            video.audio.write_audiofile(temp_audio, verbose=False)
            video.close()
        
        print("Wykrywanie fragmentów ciszy...")
        silent_segments = detect_silent_segments(
            temp_audio,
            args.min_silence_len,
            args.silence_thresh
        )
        
        if not silent_segments:
            print("Nie wykryto fragmentów ciszy do usunięcia!")
            return
            
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
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

if __name__ == "__main__":
    main()