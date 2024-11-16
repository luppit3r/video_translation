import os
import pytesseract
from PIL import Image, ImageDraw, ImageFont
from googletrans import Translator
from moviepy.editor import VideoFileClip
import argparse

# Ścieżka do pliku Tesseract OCR - dostosuj jeśli nie jest w systemowym PATH
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Funkcja do tłumaczenia tekstu
def translate_text(text, dest_language="en"):
    translator = Translator()
    translation = translator.translate(text, dest=dest_language)
    return translation.text

# Funkcja do wykrywania i tłumaczenia tekstu na klatkach
def process_frame(frame, translator):
    draw = ImageDraw.Draw(frame)
    
    # Wykryj tekst i jego lokalizację
    data = pytesseract.image_to_data(frame, lang='pol', output_type=pytesseract.Output.DICT)
    num_boxes = len(data['level'])
    
    # Przetwarzanie wykrytych fragmentów tekstu
    for i in range(num_boxes):
        (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
        text = data['text'][i].strip()
        
        if text:
            translated_text = translate_text(text)
            # Zasłoń oryginalny tekst białym prostokątem
            draw.rectangle([x, y, x + w, y + h], fill="white")
            
            # Rysuj przetłumaczony tekst
            font = ImageFont.load_default()
            draw.text((x, y), translated_text, fill="black", font=font)
    
    return frame

# Funkcja do przetwarzania wideo z wybranymi punktami czasowymi
def process_video(input_video_path, output_video_path, time_points):
    video = VideoFileClip(input_video_path)
    translator = Translator()

    # Funkcja do przetwarzania każdej klatki w wybranych punktach czasowych
    def process_frame_at_time(t):
        frame = video.get_frame(t)
        pil_frame = Image.fromarray(frame)
        
        # Przetwórz klatkę i przetłumacz tekst
        processed_frame = process_frame(pil_frame, translator)
        
        # Konwersja z powrotem do formatu numpy array
        return np.array(processed_frame)

    # Tworzenie nowego wideo
    new_frames = []
    for t in time_points:
        frame = process_frame_at_time(t)
        new_frames.append((t, frame))  # Dodaj przetworzoną klatkę z czasem

    # Przetworzony film z oryginalnym dźwiękiem
    final_video = video.fl_time(lambda t: [frame for time, frame in new_frames if abs(time - t) < 0.5][0] if any(abs(time - t) < 0.5 for time in time_points) else video.get_frame(t))
    final_video.write_videofile(output_video_path, codec="libx264", audio_codec="aac")

# Główna funkcja, która przyjmuje argumenty z wiersza poleceń
def main():
    parser = argparse.ArgumentParser(description="Translate text in video at specified times.")
    parser.add_argument("input_video", help="Path to the input video file")
    parser.add_argument("output_video", help="Path to the output video file")
    parser.add_argument("time_points", nargs='+', type=float, help="List of time points (in seconds) where Polish text appears")
    args = parser.parse_args()

    process_video(args.input_video, args.output_video, args.time_points)

if __name__ == "__main__":
    main()