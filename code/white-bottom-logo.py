import cv2
import numpy as np
from tqdm import tqdm
import os
import subprocess
import sys

def remove_orange_bar_and_add_logo(input_file, output_file, logo_path="logo.png", 
                                   bar_height=56, logo_margin_right=10, logo_margin_bottom=50):
    """
    Usuwa pomarańczowy pasek z dołu video i dodaje logo.
    
    Args:
        input_file: Ścieżka do pliku wejściowego
        output_file: Ścieżka do pliku wyjściowego  
        logo_path: Ścieżka do logo (default: "logo.png")
        bar_height: Wysokość usuwanego paska w pikselach (default: 56)
        logo_margin_right: Margines logo od prawej krawędzi (default: 10)
        logo_margin_bottom: Margines logo od dolnej krawędzi (default: 50)
    """
    
    # Sprawdzenie, czy logo istnieje
    if not os.path.isfile(logo_path):
        raise FileNotFoundError(f"Logo file {logo_path} not found! Please ensure the file exists in the project root.")

    # Wczytanie logo
    print(f"Loading logo: {logo_path}")
    logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
    if logo is None:
        raise FileNotFoundError(f"Unable to read logo file {logo_path}.")

    # Wczytanie video
    print(f"Opening video: {input_file}")
    video = cv2.VideoCapture(input_file)
    if not video.isOpened():
        raise FileNotFoundError(f"Unable to open video file {input_file}")
    
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = video.get(cv2.CAP_PROP_FPS)
    
    print(f"Video info: {width}x{height}, {fps:.2f}fps, {total_frames} frames")
    
    # Skalowanie logo do odpowiedniego rozmiaru
    logo_height, logo_width = logo.shape[:2]
    scale_factor = 0.15  # Zmień, aby dostosować wielkość logo
    new_logo_width = int(width * scale_factor)
    new_logo_height = int((logo_height / logo_width) * new_logo_width)
    logo = cv2.resize(logo, (new_logo_width, new_logo_height), interpolation=cv2.INTER_AREA)
    
    print(f"Logo scaled to: {new_logo_width}x{new_logo_height}")

    # Podział na kanały (jeśli logo ma przezroczystość)
    if logo.shape[2] == 4:  # Sprawdzenie, czy logo ma kanał alfa
        logo_alpha = logo[:, :, 3] / 255.0
        logo_rgb = logo[:, :, :3]
        print("Logo has transparency (alpha channel)")
    else:
        logo_alpha = np.ones((logo.shape[0], logo.shape[1]), dtype=np.float32)
        logo_rgb = logo
        print("Logo without transparency")

    # Pozycja logo (z parametryzacją)
    x_offset = width - new_logo_width - logo_margin_right
    y_offset = height - new_logo_height - logo_margin_bottom
    
    print(f"Logo position: ({x_offset}, {y_offset})")
    print(f"White bar: removing bottom {bar_height} pixels")

    # Sprawdzenie czy logo mieści się w ramach video
    if y_offset < 0 or x_offset < 0:
        print("Warning: Logo may be too large for video dimensions!")

    # Przygotowanie pliku tymczasowego (bez audio)
    temp_file = "temp_no_audio.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_file, fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise RuntimeError("Unable to create output video writer")
    
    print("Processing video frames...")
    
    try:
        for frame_num in tqdm(range(total_frames), desc="Processing frames"):
            ret, frame = video.read()
            if not ret:
                print(f"Warning: Could only process {frame_num} of {total_frames} frames")
                break

            # Usunięcie pomarańczowego paska (zastąpienie białym)
            frame[-bar_height:, :] = [255, 255, 255]

            # Dodanie logo z blend'owaniem alfa
            if y_offset >= 0 and x_offset >= 0:  # Sprawdź czy logo mieści się
                roi = frame[y_offset:y_offset+new_logo_height, x_offset:x_offset+new_logo_width]
                
                # Sprawdź czy ROI ma odpowiedni rozmiar
                if roi.shape[:2] == logo_rgb.shape[:2]:
                    blended = (logo_rgb * logo_alpha[:, :, None] + roi * (1 - logo_alpha[:, :, None])).astype(np.uint8)
                    frame[y_offset:y_offset+new_logo_height, x_offset:x_offset+new_logo_width] = blended

            out.write(frame)

    finally:
        video.release()
        out.release()
        print("Video processing completed")
    
    # Dodanie audio z oryginalnego pliku przy użyciu ffmpeg
    print("Merging audio with ffmpeg...")
    
    try:
        # Sprawdź czy ffmpeg jest dostępne
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        
        # Merge audio z video
        cmd = [
            'ffmpeg', '-y',  # -y = overwrite output
            '-i', temp_file,  # Video bez audio
            '-i', input_file,  # Oryginalny plik z audio
            '-c:v', 'copy',   # Kopiuj video bez re-encoding
            '-c:a', 'aac',    # Audio codec
            '-map', '0:v:0',  # Użyj video z pierwszego pliku
            '-map', '1:a:0',  # Użyj audio z drugiego pliku
            output_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Audio merge completed successfully")
        
    except FileNotFoundError:
        print("Error: ffmpeg not found in PATH!")
        print("Please install ffmpeg or add it to your system PATH")
        print(f"Temporary file saved as: {temp_file}")
        return False
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        print(f"Temporary file saved as: {temp_file}")
        return False
        
    finally:
        # Cleanup - usuń tymczasowy plik tylko jeśli wszystko OK
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                print("Temporary file cleaned up")
            except OSError as e:
                print(f"Warning: Could not remove temporary file {temp_file}: {e}")
    
    print(f"[SUKCES] Process completed successfully: {output_file}")
    return True

def main():
    if len(sys.argv) < 3:
        print("Usage: python white-bottom-logo.py input.mp4 output.mp4 [logo.png]")
        print("  input.mp4  - Input video file")
        print("  output.mp4 - Output video file") 
        print("  logo.png   - Logo file (optional, default: logo.png)")
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_video = sys.argv[2]
    
    # Logo path - opcjonalny trzeci argument lub default
    if len(sys.argv) >= 4:
        logo_path = sys.argv[3]
    else:
        logo_path = "logo.png"
    
    print("🎨 White Bottom Logo Processor")
    print(f"Input: {input_video}")
    print(f"Output: {output_video}")
    print(f"Logo: {logo_path}")
    print("-" * 50)
    
    try:
        success = remove_orange_bar_and_add_logo(input_video, output_video, logo_path)
        if success:
            print("\n🎉 Video processing completed successfully!")
        else:
            print("\n[BLAD] Video processing failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[BLAD] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()