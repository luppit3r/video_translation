<<<<<<< Updated upstream
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
=======
import sys
import os
import tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from deep_translator import GoogleTranslator
from moviepy.editor import VideoFileClip
import argparse
from tqdm import tqdm
import re
import subprocess
import uuid
import easyocr

# Inicjalizacja EasyOCR z językiem polskim
reader = easyocr.Reader(['pl'])

def create_temp_path(suffix='.png'):
    """Tworzenie prawidłowej ścieżki pliku tymczasowego."""
    temp_dir = tempfile.gettempdir()
    unique_filename = f"temp_{uuid.uuid4().hex}{suffix}"
    return os.path.join(temp_dir, unique_filename)
def run_easyocr(image):
    """Uruchom EasyOCR na obrazie i zwróć wyniki."""
    try:
        if isinstance(image, np.ndarray):
            image = Image.fromarray(image)
        image = enhance_image(image)  # Przetworzenie obrazu przed OCR
        
        results = reader.readtext(np.array(image), detail=1, paragraph=True)
        
        ocr_results = []
        for result in results:
            if len(result) == 3:
                bbox, text, confidence = result
                if confidence > 0.5:  # Filtruj wyniki o niskiej pewności
                    x_min = min(bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0])
                    y_min = min(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
                    x_max = max(bbox[0][0], bbox[1][0], bbox[2][0], bbox[3][0])
                    y_max = max(bbox[0][1], bbox[1][1], bbox[2][1], bbox[3][1])
                    
                    ocr_results.append({
                        'text': text,
                        'confidence': confidence * 100,  # Konwersja na wartość procentową
                        'box': (x_min, y_min, x_max - x_min, y_max - y_min)
                    })
        
        print("Wynik OCR (EasyOCR):", ocr_results)
        return ocr_results
        
    except Exception as e:
        print(f"Błąd OCR z EasyOCR: {str(e)}")
        return []

def enhance_image(image):
    """Ulepszone przetwarzanie obrazu."""
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    
    # Konwersja do RGB, jeśli potrzebna
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save("step1_rgb_conversion.png")  # Zapisz obraz po konwersji do RGB
    
    # Zwiększ rozmiar
    width, height = image.size
    image = image.resize((width * 3, height * 3), Image.Resampling.LANCZOS)
    image.save("step2_resized.png")  # Zapisz obraz po zwiększeniu rozmiaru
    
    # Konwersja do skali szarości
    gray_image = image.convert('L')
    gray_image.save("step3_grayscale.png")  # Zapisz obraz po konwersji do skali szarości
    
    # Zwiększ kontrast
    enhancer = ImageEnhance.Contrast(gray_image)
    enhanced = enhancer.enhance(4.0)  # Jeszcze większy kontrast
    enhanced.save("step4_contrast.png")  # Zapisz obraz po zwiększeniu kontrastu
    
    # Dodaj wyostrzenie obrazu
    sharpener = ImageEnhance.Sharpness(enhanced)
    enhanced = sharpener.enhance(3.0)  # Większe wyostrzenie
    enhanced.save("step5_sharpened.png")  # Zapisz obraz po wyostrzeniu
    
    return enhanced

def process_frame(frame, confidence_threshold=50):
    """Przetwarzanie klatki."""
    if isinstance(frame, np.ndarray):
        frame = Image.fromarray(frame)
    
    try:
        # Przygotuj obraz
        enhanced = enhance_image(frame)
        
        # Wykonaj OCR przy użyciu EasyOCR
        results = run_easyocr(enhanced)
        
        # Grupuj wyniki
        grouped_results = {}
        y_threshold = 50
        
        for result in results:
            if result['confidence'] < confidence_threshold:
                continue
                
            text = result['text'].strip()
            # Ignoruj pojedyncze znaki i liczby
            if len(text) <= 1 or text.isdigit() or all(c in 'ABCDEkNm/' for c in text):
                continue
                
            y = result['box'][1]
            y_group = y // y_threshold * y_threshold
            
            if y_group not in grouped_results:
                grouped_results[y_group] = []
            grouped_results[y_group].append(result)
        
        # Rysuj tłumaczenia
        draw = ImageDraw.Draw(frame)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        texts_found = False
        
        for group in grouped_results.values():
            group.sort(key=lambda x: x['box'][0])
            text = ' '.join(r['text'] for r in group)
            
            if text.strip():
                texts_found = True
                print(f"Wykryto tekst: '{text}'")
                
                try:
                    translator = GoogleTranslator(source='pl', target='en')
                    translated = translator.translate(text)
                    print(f"Przetłumaczono: '{text}' -> '{translated}'")
                    
                    x_min = min(r['box'][0] for r in group)
                    y_min = min(r['box'][1] for r in group)
                    x_max = max(r['box'][0] + r['box'][2] for r in group)
                    y_max = max(r['box'][1] + r['box'][3] for r in group)
                    
                    padding = 10
                    draw.rectangle(
                        [x_min-padding, y_min-padding, x_max+padding, y_max+padding],
                        fill="white",
                        outline="black"
                    )
                    draw.text((x_min, y_min), translated, fill="black", font=font)
                    
                except Exception as e:
                    print(f"Błąd tłumaczenia: {str(e)}")
        
        if not texts_found:
            print("Nie wykryto żadnego tekstu do tłumaczenia w tej klatce")
        
        return np.array(frame)
        
    except Exception as e:
        print(f"Błąd przetwarzania klatki: {str(e)}")
        return np.array(frame)





def time_to_seconds(time_str):
    """Konwertuj czas z formatu MM:SS na sekundy."""
    try:
        match = re.match(r'^(\d+):([0-5]?\d([.]\d+)?)$', time_str)
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            return minutes * 60 + seconds
        else:
            raise ValueError
    except ValueError:
        print(f"Błędny format czasu: {time_str}. Użyj formatu MM:SS lub MM:SS.ms (np. 1:23 lub 1:23.5)")
        return None

def process_video(input_path, output_path, time_points, chunk_duration=1.0):
    """Przetwarzanie wideo z obsługą błędów."""
    try:
        video = VideoFileClip(input_path)
        fps = video.fps
        
        time_points = sorted(set(t for t in time_points if 0 <= t <= video.duration))
        
        if not time_points:
            raise ValueError("Brak prawidłowych punktów czasowych do przetworzenia!")
        
        print(f"Przetwarzanie {len(time_points)} punktów czasowych...")
        
        processed_frames = {}
        for t in tqdm(time_points, desc="Przetwarzanie klatek"):
            try:
                frame = video.get_frame(t)
                processed = process_frame(frame)
                processed_frames[t] = processed
            except Exception as e:
                print(f"Błąd przetwarzania klatki w czasie {t}s: {str(e)}")
                processed_frames[t] = frame
        
        def frame_modifier(get_frame, t):
            nearest_time = min(time_points, key=lambda x: abs(x - t))
            if abs(nearest_time - t) < chunk_duration/2:
                return processed_frames[nearest_time]
            return get_frame(t)
        
        print("Zapisywanie przetworzonego wideo...")
        final_video = video.fl(frame_modifier)
        
        final_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            preset="faster",
            threads=4,
            fps=fps,
            verbose=False
        )
        
        final_video.close()
        video.close()
        
    except Exception as e:
        print(f"Wystąpił błąd podczas przetwarzania wideo: {str(e)}")
        try:
            if 'final_video' in locals():
                final_video.close()
            if 'video' in locals():
                video.close()
        except:
            pass
        raise

def main():
    parser = argparse.ArgumentParser(description="Tłumacz tekst w wideo w określonych momentach.")
    parser.add_argument("input_video", help="Ścieżka do pliku wejściowego")
    parser.add_argument("output_video", help="Ścieżka do pliku wyjściowego")
    parser.add_argument("time_points", nargs='+',
                        help="Lista punktów czasowych w formacie MM:SS lub MM:SS.ms (np. 1:23 lub 1:23.5)")
    parser.add_argument("--confidence", type=int, default=50,
                        help="Próg pewności OCR (0-100)")
    parser.add_argument("--chunk_duration", type=float, default=1.0,
                        help="Czas trwania zmodyfikowanej klatki (sekundy)")
    
    args = parser.parse_args()
    
    # Konwersja czasów
    time_points = []
    for time_str in args.time_points:
        seconds = time_to_seconds(time_str)
        if seconds is not None:
            time_points.append(seconds)
        else:
            return
    
    if not time_points:
        print("Nie podano prawidłowych punktów czasowych!")
        return
    
    print(f"Punkty czasowe do przetworzenia: {[f'{int(t//60)}:{t%60:05.2f}' for t in time_points]}")
    print(f"Używany próg pewności OCR: {args.confidence}")
    
    try:
        process_video(
            args.input_video,
            args.output_video,
            time_points,
            args.chunk_duration
        )
        print("Zakończono przetwarzanie!")
        
    except Exception as e:
        print(f"Wystąpił błąd: {str(e)}")
        sys.exit(1)
>>>>>>> Stashed changes

if __name__ == "__main__":
    main()