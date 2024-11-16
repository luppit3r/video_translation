import os
import argparse
from pathlib import Path
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
from pydub import AudioSegment

def read_translated_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    timestamps = []
    sentences = []
    for line in lines:
        parts = line.split(', ')
        start = float(parts[0].split(': ')[1])
        end = float(parts[1].split(': ')[1])
        sentence = parts[2].split(': ')[1].strip()
        timestamps.append((start, end))
        sentences.append(sentence)
    
    return timestamps, sentences

def adjust_timestamps(timestamps, audio_durations):
    adjusted_timestamps = []
    current_time = 0

    for (start, end), duration in zip(timestamps, audio_durations):
        adjusted_start = max(start, current_time)
        adjusted_end = adjusted_start + duration
        adjusted_timestamps.append((adjusted_start, adjusted_end))
        current_time = adjusted_end

    return adjusted_timestamps

def synchronize_audio_with_video(video_file_path, timestamps, audio_dir, output_video_path):
    video_clip = VideoFileClip(str(video_file_path))
    audio_clips = []
    audio_durations = []

    # First, get all audio durations
    for i, (start, end) in enumerate(timestamps):
        audio_file_path = audio_dir / f"output_audio_{i}.mp3"
        audio_clip = AudioFileClip(str(audio_file_path))
        audio_durations.append(audio_clip.duration)

    # Adjust timestamps
    adjusted_timestamps = adjust_timestamps(timestamps, audio_durations)

    # Now create audio clips with adjusted timestamps
    for i, (start, end) in enumerate(adjusted_timestamps):
        audio_file_path = audio_dir / f"output_audio_{i}.mp3"
        audio_clip = AudioFileClip(str(audio_file_path))
        audio_clip = audio_clip.set_start(start)
        audio_clips.append(audio_clip)
        
        print(f"Processed audio segment {i}: start={start}s, duration={audio_clip.duration}s")

    # Combine all audio clips
    final_audio = CompositeAudioClip(audio_clips)

    # Set the audio of the video clip
    final_video = video_clip.set_audio(final_audio)

    # Write the final video file
    final_video.write_videofile(str(output_video_path), codec="libx264", audio_codec="aac")

def main():
    parser = argparse.ArgumentParser(description="Synchronize audio with video using translated text file.")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("video_file", help="Path to the input video file")
    parser.add_argument("--audio_dir", default="generated", help="Directory containing generated audio files")
    parser.add_argument("--start_time", type=float, default=0.0, help="Start time of the video segment (in seconds)")
    parser.add_argument("--end_time", type=float, help="End time of the video segment (in seconds)")
    args = parser.parse_args()

    input_file = Path(args.input_file)
    video_file = Path(args.video_file)
    
    # Adjust audio_dir to be relative to the main directory
    main_dir = input_file.parents[1]
    audio_dir = main_dir / args.audio_dir / video_file.stem

    # Create output directory in the main folder
    output_dir = main_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_video_path = output_dir / f"{video_file.stem}_synchronized.mp4"

    timestamps, _ = read_translated_file(input_file)

# Filtruj segmenty według start_time i end_time
    filtered_timestamps = [
        (start, end) 
        for (start, end) in timestamps 
        if start >= args.start_time and (args.end_time is None or end <= args.end_time)
    ]

    synchronize_audio_with_video(video_file, filtered_timestamps, audio_dir, output_video_path)
    print(f"Synchronized video saved to: {output_video_path}")

if __name__ == "__main__":
    main()