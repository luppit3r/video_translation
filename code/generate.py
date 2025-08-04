import os
import re
import requests
import argparse
from pathlib import Path

# API key should be set via environment variable
os.environ['ELEVENLABS_API_KEY'] = "sk_1f61682e0b96b0f53580d385ad097ec8ee062217127058fc"
CHUNK_SIZE = 1024  # Size of chunks to read/write at a time
XI_API_KEY = os.getenv('ELEVENLABS_API_KEY')  # Your API key for authentication
VOICE_ID = "XfNU2rGpBa01ckF309OY"  # ID of the voice model to use

def read_translated_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    timestamps = []
    sentences = []
    for line in lines:
        # Use regular expressions to extract start, end, and sentence
        match = re.match(r'Start: ([\d.]+), End: ([\d.]+), Sentence: (.+)', line)
        if match:
            start = float(match.group(1))
            end = float(match.group(2))
            sentence = match.group(3).strip()
            timestamps.append((start, end))
            sentences.append(sentence)

    return timestamps, sentences

def generate_audio(text, api_key, voice_id, output_path):
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    data = {
        "text": text,
        "model_id": "eleven_turbo_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }

    response = requests.post(tts_url, headers=headers, json=data, stream=True)

    if response.ok:
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
        return output_path
    else:
        print(f"Failed to generate audio for text: {text}")
        raise Exception(f"Failed to generate audio: {response.text}")

def main():
    parser = argparse.ArgumentParser(description="Generate audio files from translated text file.")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("video_file", help="Path to the video file")
    args = parser.parse_args()

    input_file = Path(args.input_file)
    video_file = Path(args.video_file)

    # Create output directory in the parent folder of the input file
    output_dir = input_file.parents[1] / "generated" / video_file.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    elevenlabs_api_key = XI_API_KEY

    timestamps, sentences = read_translated_file(input_file)

    for i, sentence in enumerate(sentences):
        audio_file_path = output_dir / f"output_audio_{i}.mp3"
        generate_audio(sentence, elevenlabs_api_key, VOICE_ID, str(audio_file_path))
        print(f"Generated audio file for sentence {i}: {audio_file_path}")

# Dodaj dźwięk zakończenia
    import winsound
    winsound.Beep(1000, 500)  # Sygnał o częstotliwości 1000Hz trwający 500ms

if __name__ == "__main__":
    main()