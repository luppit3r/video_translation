import os
import sys
import argparse
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")
from openai import OpenAI

# Hardcoded API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def split_text(text, max_tokens=3800):
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_length = 0
    
    for line in lines:
        line_length = len(line) + 1  # +1 for the newline character
        if current_length + line_length > max_tokens:
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_length = line_length
        else:
            current_chunk.append(line)
            current_length += line_length
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def translate_text(text):
    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "Translate the following text to English, keep timestamps and format intact"
            },
            {
                "role": "user",
                "content": text
            },
        ],
        temperature=1,
        max_tokens=4000,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].message.content

from pathlib import Path

def save_translated_text(file_path, content):
    # Utwórz katalogi, jeśli nie istnieją
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def main():
    parser = argparse.ArgumentParser(description="Translate a text file to English using OpenAI's API.")
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument("output_file", help="Path to the output file")
    args = parser.parse_args()

    # Read content from the file
    content = read_file(args.input_file)

    # Split content into manageable chunks
    chunks = split_text(content)

     # Translate each chunk and display progress
    translated_chunks = []
    total_chunks = len(chunks)
    for i, chunk in enumerate(chunks, start=1):
        print(f"Translating chunk {i}/{total_chunks}...")
        translated_chunk = translate_text(chunk)
        translated_chunks.append(translated_chunk)

          # Combine the results
    translated_content = '\n'.join(translated_chunks)

    # Save the translated content to a new file
    save_translated_text(args.output_file, translated_content)
    print(f"Translation completed. Output saved to {args.output_file}")

if __name__ == "__main__":
    main()