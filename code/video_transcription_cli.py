import argparse
import json
import re
import os
import sys
import time
import traceback

def log(message):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def safe_import(module_name):
    try:
        return __import__(module_name)
    except ImportError as e:
        log(f"Error importing {module_name}: {e}")
        log(f"Please ensure {module_name} is installed correctly in your virtual environment.")
        sys.exit(1)

ffmpeg = safe_import('ffmpeg')
whisper = safe_import('whisper')

def extract_audio(video_path, audio_path):
    log(f"Starting audio extraction from {video_path}")
    if not os.path.exists(video_path):
        log(f"Error: Video file {video_path} does not exist")
        return False

    try:
        log("Running ffmpeg for audio extraction...")
        ffmpeg.input(video_path).output(audio_path).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        log("Audio extraction successful")
        return True
    except ffmpeg.Error as e:
        log(f"Error occurred during audio extraction: {e.stderr.decode('utf-8')}")
        return False

def transcribe_audio_with_whisper(audio_path):
    log("Loading Whisper model (this may take a moment)...")
    model = whisper.load_model("base")  # Changed to "base" for faster loading
    log("Whisper model loaded successfully")
    
    log(f"Starting transcription of {audio_path}")
    result = model.transcribe(audio_path)
    log("Transcription completed successfully")
    return result

def split_into_sentences(transcription_result):
    log("Splitting transcription into sentences")
    sentences = []
    for segment in transcription_result['segments']:
        sentences.append({
            "start": segment['start'],
            "end": segment['end'],
            "sentence": segment['text'].strip()
        })
    log(f"Split transcription into {len(sentences)} sentences")
    return sentences

def save_sentences_to_file(sentences, output_filename):
    log(f"Saving sentences to {output_filename}")
    with open(output_filename, "w", encoding='utf-8') as f:
        for sentence in sentences:
            f.write(f"Start: {sentence['start']:.2f}, End: {sentence['end']:.2f}, Sentence: {sentence['sentence']}\n")
    log("Sentences saved successfully")

def process_video(input_path):
    log(f"Starting processing of video: {input_path}")
    
    try:
        # Create subfolders
        base_dir = os.path.dirname(input_path)
        audio_dir = os.path.join(base_dir, 'audio')
        text_dir = os.path.join(base_dir, 'text')
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(text_dir, exist_ok=True)
        log(f"Created output directories: {audio_dir} and {text_dir}")

        # Generate output paths
        video_name = os.path.splitext(os.path.basename(input_path))[0]
        audio_path = os.path.join(audio_dir, f"{video_name}.wav")
        transcription_path = os.path.join(text_dir, f"{video_name}_transcription.json")
        sentences_path = os.path.join(text_dir, f"{video_name}_sentences.txt")

        # Process video
        if extract_audio(input_path, audio_path):
            transcription_result = transcribe_audio_with_whisper(audio_path)
            
            log(f"Saving transcription to {transcription_path}")
            with open(transcription_path, "w", encoding='utf-8') as f:
                json.dump(transcription_result, f, indent=4, ensure_ascii=False)
            log("Transcription saved successfully")
            
            sentences = split_into_sentences(transcription_result)
            save_sentences_to_file(sentences, sentences_path)
            
            log(f"Processing complete for {input_path}")
            log(f"Audio saved to: {audio_path}")
            log(f"Transcription saved to: {transcription_path}")
            log(f"Sentences saved to: {sentences_path}")
        else:
            log(f"Failed to process {input_path}")
    except Exception as e:
        log(f"An error occurred while processing {input_path}")
        log(f"Error details: {str(e)}")
        log("Stack trace:")
        log(traceback.format_exc())

def main():
    parser = argparse.ArgumentParser(description="Process video files for transcription.")
    parser.add_argument("input_path", help="Path to the video file or directory containing video files")
    args = parser.parse_args()

    log("Starting video transcription CLI")
    log(f"Input path: {args.input_path}")

    try:
        if os.path.isfile(args.input_path):
            process_video(args.input_path)
        elif os.path.isdir(args.input_path):
            log(f"Processing directory: {args.input_path}")
            for root, _, files in os.walk(args.input_path):
                for file in files:
                    if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        video_path = os.path.join(root, file)
                        process_video(video_path)
        else:
            log(f"Error: Invalid input path: {args.input_path}")
    except Exception as e:
        log(f"An unexpected error occurred: {str(e)}")
        log("Stack trace:")
        log(traceback.format_exc())

    log("Video transcription CLI completed")

if __name__ == "__main__":
    main()