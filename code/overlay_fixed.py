import os
import re
import argparse
from pathlib import Path

try:
    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
    from pydub import AudioSegment
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install: pip install moviepy pydub")
    exit(1)

def read_translated_file(file_path):
    """
    Poprawiona funkcja do odczytu pliku z timestampami i zdaniami.
    Używa regex zamiast split() żeby obsłużyć przecinki w zdaniach.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    timestamps = []
    sentences = []
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:  # Pomiń puste linie
            continue
            
        # Użyj regex do precyzyjnego parsowania
        match = re.match(r'Start:\s*([\d.]+),\s*End:\s*([\d.]+),\s*Sentence:\s*(.+)', line)
        
        if match:
            try:
                start = float(match.group(1))
                end = float(match.group(2))
                sentence = match.group(3).strip()
                
                timestamps.append((start, end))
                sentences.append(sentence)
                
                print(f"Line {line_num}: {start}s-{end}s | '{sentence[:50]}{'...' if len(sentence) > 50 else ''}'")
                
            except ValueError as e:
                print(f"Warning: Could not parse timestamps on line {line_num}: {line}")
                print(f"Error: {e}")
                continue
        else:
            print(f"Warning: Line {line_num} doesn't match expected format: {line}")
    
    print(f"Successfully parsed {len(timestamps)} sentences from {file_path}")
    return timestamps, sentences

def adjust_timestamps(timestamps, audio_durations):
    """
    Dopasowuje timestampy żeby audio się nie nakładało.
    """
    adjusted_timestamps = []
    current_time = 0

    for i, ((start, end), duration) in enumerate(zip(timestamps, audio_durations)):
        # Upewnij się że nowy segment zaczyna się po zakończeniu poprzedniego
        adjusted_start = max(start, current_time)
        adjusted_end = adjusted_start + duration
        
        adjusted_timestamps.append((adjusted_start, adjusted_end))
        current_time = adjusted_end
        
        # Debug info
        if adjusted_start != start:
            print(f"Adjusted segment {i}: {start}s -> {adjusted_start}s (prevented overlap)")

    return adjusted_timestamps

def synchronize_audio_with_video(video_file_path, timestamps, audio_dir, output_video_path):
    """
    Główna funkcja synchronizacji audio z video.
    """
    print(f"Loading video: {video_file_path}")
    
    try:
        video_clip = VideoFileClip(str(video_file_path))
        print(f"Video loaded: {video_clip.duration:.2f}s, {video_clip.fps}fps")
    except Exception as e:
        print(f"Error loading video: {e}")
        return False
    
    audio_clips = []
    audio_durations = []

    # Pierwsza pętla: wczytaj wszystkie pliki audio i sprawdź długości
    print("\n--- Checking audio files ---")
    for i, (start, end) in enumerate(timestamps):
        audio_file_path = audio_dir / f"output_audio_{i}.mp3"
        
        print(f"Checking audio file {i}: {audio_file_path}")
        
        if not audio_file_path.exists():
            print(f"[BLAD] Error: Audio file {audio_file_path} does not exist.")
            return False
        
        try:
            audio_clip = AudioFileClip(str(audio_file_path))
            audio_durations.append(audio_clip.duration)
            print(f"[OK] Audio {i}: {audio_clip.duration:.2f}s")
            audio_clip.close()  # Zwolnij pamięć
        except Exception as e:
            print(f"[BLAD] Error loading audio file {i}: {e}")
            return False

    # Dopasuj timestampy
    print("\n--- Adjusting timestamps ---")
    adjusted_timestamps = adjust_timestamps(timestamps, audio_durations)

    # Druga pętla: stwórz finalne audio clips z dopasowanymi timestampami
    print("\n--- Creating final audio composition ---")
    for i, (start, end) in enumerate(adjusted_timestamps):
        audio_file_path = audio_dir / f"output_audio_{i}.mp3"
        
        try:
            audio_clip = AudioFileClip(str(audio_file_path))
            audio_clip = audio_clip.set_start(start)
            audio_clips.append(audio_clip)
            
            print(f"Audio segment {i}: start={start:.2f}s, duration={audio_clip.duration:.2f}s")
        except Exception as e:
            print(f"Error processing audio segment {i}: {e}")
            return False

    # Połącz wszystkie audio clips
    print("\n--- Compositing final audio ---")
    try:
        final_audio = CompositeAudioClip(audio_clips)
        print(f"Final audio duration: {final_audio.duration:.2f}s")
    except Exception as e:
        print(f"Error compositing audio: {e}")
        return False

    # Zastąp audio w video
    print("\n--- Creating final video ---")
    try:
        final_video = video_clip.set_audio(final_audio)
        
        print(f"Writing video to: {output_video_path}")
        final_video.write_videofile(
            str(output_video_path), 
            codec="libx264", 
            audio_codec="aac",
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        print(f"[SUKCES] Synchronized video saved to: {output_video_path}")
        
        # Cleanup
        final_video.close()
        video_clip.close()
        final_audio.close()
        for clip in audio_clips:
            clip.close()
            
        return True
        
    except Exception as e:
        print(f"[BLAD] Error creating final video: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Synchronize audio with video using translated text file.")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("video_file", help="Path to the input video file")
    parser.add_argument("--audio_dir", default="generated", help="Directory containing generated audio files")
    args = parser.parse_args()

    # Ścieżki
    input_file = Path(args.input_file)
    video_file = Path(args.video_file)
    
    # Sprawdź czy pliki istnieją
    if not input_file.exists():
        print(f"[BLAD] Error: Input file {input_file} does not exist.")
        return
    
    if not video_file.exists():
        print(f"[BLAD] Error: Video file {video_file} does not exist.")
        return
    
    # Katalog audio - relatywny do głównego katalogu
    main_dir = input_file.parents[1]
    if Path(args.audio_dir).is_absolute():
        audio_dir = Path(args.audio_dir)
    else:
        audio_dir = main_dir / args.audio_dir / video_file.stem

    if not audio_dir.exists():
        print(f"[BLAD] Error: Audio directory {audio_dir} does not exist.")
        return

    # Katalog output
    output_dir = main_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_video_path = output_dir / f"{video_file.stem}_synchronized.mp4"

    print(f"Input file: {input_file}")
    print(f"Video file: {video_file}")
    print(f"Audio directory: {audio_dir}")
    print(f"Output video: {output_video_path}")
    print("-" * 50)

    # Wczytaj timestamps i zdania
    try:
        timestamps, sentences = read_translated_file(input_file)
    except Exception as e:
        print(f"[BLAD] Error reading input file: {e}")
        return

    if not timestamps:
        print("[BLAD] No valid timestamps found in input file.")
        return

    # Synchronizuj
    success = synchronize_audio_with_video(video_file, timestamps, audio_dir, output_video_path)
    
    if success:
        print(f"\n[SUKCES] Success! Synchronized video saved to: {output_video_path}")
        
        # Dźwięk zakończenia
        try:
            import winsound
            winsound.Beep(1000, 500)
        except ImportError:
            print("[DZWONEK] Process completed!")  # Fallback dla nie-Windows
    else:
        print("\n[BLAD] Process failed!")

if __name__ == "__main__":
    main()