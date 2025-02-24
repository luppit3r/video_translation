import cv2
import numpy as np
from tqdm import tqdm
import os

def remove_orange_bar_and_add_logo(input_file, output_file, logo_path="logo.png"):
    # Sprawdzenie, czy logo istnieje w domyślnej ścieżce
    if not os.path.isfile(logo_path):
        raise FileNotFoundError(f"Logo file {logo_path} not found! Please ensure the file exists in the project root.")

    # Wczytanie logo
    logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
    if logo is None:
        raise FileNotFoundError(f"Unable to read logo file {logo_path}.")

    video = cv2.VideoCapture(input_file)
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = video.get(cv2.CAP_PROP_FPS)
    
    # Skalowanie logo do odpowiedniego rozmiaru
    logo_height, logo_width = logo.shape[:2]
    scale_factor = 0.15  # Zmień, aby dostosować wielkość logo
    new_logo_width = int(width * scale_factor)
    new_logo_height = int((logo_height / logo_width) * new_logo_width)
    logo = cv2.resize(logo, (new_logo_width, new_logo_height), interpolation=cv2.INTER_AREA)

    # Podział na kanały (jeśli logo ma przezroczystość)
    if logo.shape[2] == 4:  # Sprawdzenie, czy logo ma kanał alfa
        logo_alpha = logo[:, :, 3] / 255.0
        logo_rgb = logo[:, :, :3]
    else:
        logo_alpha = np.ones((logo.shape[0], logo.shape[1]), dtype=np.float32)
        logo_rgb = logo

    # Pozycja logo
    x_offset = width - new_logo_width - 10  # 10 pikseli od prawej krawędzi
    y_offset = height - new_logo_height - 50  # 10 pikseli od dolnej krawędzi

    # Przygotowanie pliku tymczasowego (bez audio)
    temp_file = "temp_no_audio.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_file, fourcc, fps, (width, height))
    
    for _ in tqdm(range(total_frames), desc="Processing frames"):
        ret, frame = video.read()
        if not ret:
            break

        # Usunięcie pomarańczowego paska
        frame[-56:, :] = [255, 255, 255]

        # Dodanie logo
        roi = frame[y_offset:y_offset+new_logo_height, x_offset:x_offset+new_logo_width]
        blended = (logo_rgb * logo_alpha[:, :, None] + roi * (1 - logo_alpha[:, :, None])).astype(np.uint8)
        frame[y_offset:y_offset+new_logo_height, x_offset:x_offset+new_logo_width] = blended

        out.write(frame)

    video.release()
    out.release()
    
    # Dodanie audio z oryginalnego pliku
    from subprocess import call
    print("Merging audio...")
    call(['ffmpeg', '-i', temp_file, '-i', input_file, '-c:v', 'copy', '-c:a', 'aac', output_file])
    
    # Usunięcie pliku tymczasowego
    os.remove(temp_file)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python code/white-bottom-logo.py input.mp4 output.mp4")
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_video = sys.argv[2]

    # Domyślna ścieżka do logo
    default_logo_path = "logo.png"
    
    # Wywołanie funkcji z domyślnym logo
    remove_orange_bar_and_add_logo(input_video, output_video, default_logo_path)