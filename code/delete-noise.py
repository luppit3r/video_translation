import argparse
import numpy as np
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from pydub import AudioSegment
import logging
from pathlib import Path
import os

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_amplitude_spikes(audio_path, threshold=0.3, min_duration=0.3, max_duration=0.45, silence_threshold=0.05, silence_duration=0.1):
    """
    Wykrywa krótkie skoki amplitudy w audio, które są otoczone ciszą po prawej stronie.
    """
    logger.info(f"Wczytywanie pliku audio: {audio_path}")
    audio = AudioSegment.from_file(audio_path)
    logger.info(f"Długość audio: {len(audio)/1000.0} sekund")
    
    samples = np.array(audio.get_array_of_samples())
    
    # Obliczanie RMS w oknach czasowych
    window_size = int(0.02 * audio.frame_rate)  # 20ms okno
    rms = []
    
    logger.info("Obliczanie RMS dla okien czasowych...")
    for i in range(0, len(samples), window_size):
        window = samples[i:i+window_size]
        rms.append(np.sqrt(np.mean(np.square(window))))
    
    rms = np.array(rms)
    rms_normalized = rms / max(rms)
    
    logger.info(f"Szukanie skoków amplitudy z cichym otoczeniem po prawej stronie...")
    segments = []
    potential_segments = []
    spike_start = None
    
    # Znajdź wszystkie potencjalne segmenty
    for i in range(len(rms_normalized)):
        if rms_normalized[i] > threshold:
            if spike_start is None:
                spike_start = i
        elif spike_start is not None:
            spike_end = i
            duration = (spike_end - spike_start) * 0.02
            
            if min_duration <= duration <= max_duration:
                potential_segments.append((spike_start, spike_end))
            spike_start = None
    
    logger.info(f"Znaleziono {len(potential_segments)} potencjalnych segmentów")
    
    # Sprawdź ciszę tylko po prawej stronie każdego segmentu
    silence_windows = int(silence_duration / 0.02)
    
    for spike_start, spike_end in potential_segments:
        silence_after = True
        max_amplitude_after = 0
        
        # Sprawdź ciszę po
        for j in range(spike_end, min(len(rms_normalized), spike_end + silence_windows)):
            if rms_normalized[j] > silence_threshold:
                silence_after = False
                max_amplitude_after = max(max_amplitude_after, rms_normalized[j])
        
        if silence_after:
            segments.append((spike_start * 0.02, spike_end * 0.02))
        else:
            logger.debug(f"Odrzucono segment {spike_start * 0.02:.2f}-{spike_end * 0.02:.2f}s: Cisza po: {silence_after} (max ampl: {max_amplitude_after:.3f})")
    
    logger.info(f"Z tego {len(segments)} segmentów spełnia kryteria ciszy po prawej stronie")
    
    return segments

def seconds_to_minsec(seconds):
    """Konwertuje sekundy na format MM:SS."""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"{minutes}:{remaining_seconds:05.2f}"

def generate_report(segments, output_path, video_duration):
    """Generuje raport o usuniętych segmentach."""
    report_path = Path(output_path).with_suffix('.txt')
    
    with open(report_path, "w", encoding="utf-8") as report_file:
        # Nagłówek raportu
        report_file.write("Raport usuwania szumów/pogłosów\n")
        report_file.write("===============================\n\n")
        
        # Informacje ogólne
        report_file.write(f"Plik wejściowy: {Path(output_path).name}\n")
        report_file.write(f"Całkowita długość wideo: {seconds_to_minsec(video_duration)}\n")
        report_file.write(f"Liczba usuniętych segmentów: {len(segments)}\n\n")
        
        # Szczegóły usuniętych segmentów
        report_file.write("Szczegóły usuniętych segmentów:\n")
        report_file.write("-----------------------------\n")
        total_duration = 0
        for i, (start, end) in enumerate(segments, 1):
            duration = end - start
            total_duration += duration
            report_file.write(
                f"Segment {i:>3}: {seconds_to_minsec(start)} -> {seconds_to_minsec(end)} "
                f"(długość: {duration:.2f}s)\n"
            )
        
        # Podsumowanie
        report_file.write(f"\nCałkowity czas usuniętych fragmentów: {total_duration:.2f}s\n")
        report_file.write(f"Procentowo usunięto: {(total_duration/video_duration)*100:.1f}% materiału\n")
    
    logger.info(f"Raport został zapisany do: {report_path}")

from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

def save_with_forced_fps(final_video, temp_file, output_video, video_fps):
    """
    Zapisuje klip finalny do pliku tymczasowego i wymusza FPS za pomocą FFmpeg.
    """
    logger.info("Zapisywanie z wymuszonym FPS za pomocą FFmpeg...")
    
    # Sprawdzenie FPS final_video
    if final_video.fps is None:
        logger.warning("FPS klipu finalnego jest None. Ustawiam domyślny FPS.")
        final_video = final_video.set_fps(video_fps)
    
    logger.info(f"Finalny klip ma FPS: {final_video.fps}")
    
    # Sprawdzenie rozmiaru
    if final_video.size is None:
        raise ValueError("Rozmiar finalnego klipu jest None.")
    
    # Zapisz finalny klip do tymczasowego pliku
    final_video.write_videofile(temp_file, codec="libx264", fps=video_fps, audio_codec="aac")
    
    # Wymuś FPS w ostatecznym pliku wyjściowym
    logger.info("Wymuszanie FPS w nowym pliku...")
    ffmpeg_extract_subclip(temp_file, 0, final_video.duration, targetname=output_video)

def process_video(input_video, output_video, threshold=0.3, min_duration=0.3, max_duration=0.45, silence_threshold=0.2, silence_duration=0.1):
    """
    Przetwarza wideo, usuwając fragmenty z krótkimi skokami amplitudy.
    """
    logger.info("Wczytywanie wideo...")
    try:
        video = VideoFileClip(input_video)
        video_duration = video.duration
        
        # Pobierz FPS z wejściowego wideo
        video_fps = video.fps or 30.0
        logger.info(f"Długość wideo: {video_duration} sekund, Używany FPS: {video_fps}")
        
        # Eksport audio do tymczasowego pliku
        temp_audio = "temp_audio.wav"
        logger.info("Eksportowanie audio...")
        video.audio.write_audiofile(temp_audio)
        
        # Wykrywanie skoków amplitudy
        logger.info("Wykrywanie skoków amplitudy...")
        spike_segments = detect_amplitude_spikes(temp_audio, threshold, min_duration, max_duration, silence_threshold, silence_duration)
        
        # Filtruj segmenty
        valid_segments = [(start, end) for start, end in spike_segments if start < video_duration and end <= video_duration]
        logger.info(f"Znaleziono {len(valid_segments)} prawidłowych segmentów do usunięcia...")
        
        # Generuj raport przed przetwarzaniem wideo
        generate_report(valid_segments, output_video, video_duration)
        
        # Tworzenie nowego wideo bez wykrytych segmentów
        clips = []
        start = 0

        for spike_start, spike_end in valid_segments:
            if start < spike_start:
                try:
                    clip = video.subclip(start, spike_start).set_fps(video_fps)
                    clips.append(clip)
                    logger.info(f"Dodano klip od {start:.2f}s do {spike_start:.2f}s")
                except Exception as clip_error:
                    logger.warning(f"Błąd podczas tworzenia klipu od {start:.2f}s do {spike_start:.2f}s: {clip_error}")
            start = spike_end

        if start < video.duration:
            try:
                clip = video.subclip(start, video.duration).set_fps(video_fps)
                clips.append(clip)
                logger.info(f"Dodano klip od {start:.2f}s do końca ({video.duration:.2f}s)")
            except Exception as clip_error:
                logger.warning(f"Błąd podczas tworzenia klipu od {start:.2f}s do końca: {clip_error}")

        if not clips:
            logger.warning("Nie znaleziono żadnych klipów do połączenia!")
            return

        # Łączenie fragmentów
        logger.info("Łączenie fragmentów...")
        try:
            final_video = concatenate_videoclips(clips, method="compose").set_fps(video_fps)
            logger.info("Pomyślnie połączono klipy.")
        except Exception as concat_error:
            logger.error(f"Błąd podczas łączenia klipów: {concat_error}")
            raise concat_error

        # Wymuszenie FPS i zapis za pomocą tymczasowego pliku
        temp_file = "temp_output.mp4"
        save_with_forced_fps(final_video, temp_file, output_video, video_fps)
        os.remove(temp_file)  # Usuń plik tymczasowy

        # Czyszczenie
        video.close()
        final_video.close()
        os.remove(temp_audio)
        logger.info("Wideo zostało pomyślnie przetworzone i zapisane.")
    except Exception as e:
        logger.error(f"Wystąpił błąd: {str(e)}")
        raise e

def main():
    parser = argparse.ArgumentParser(description="Usuwa krótkie skoki amplitudy z wideo.")
    parser.add_argument("input_video", help="Ścieżka do pliku wejściowego")
    parser.add_argument("output_video", help="Ścieżka do pliku wyjściowego")
    parser.add_argument("--threshold", type=float, default=0.15, help="Próg amplitudy (0-1)")
    parser.add_argument("--min-duration", type=float, default=0.3, help="Minimalna długość skoku (s)")
    parser.add_argument("--max-duration", type=float, default=0.45, help="Maksymalna długość skoku (s)")
    parser.add_argument("--silence-threshold", type=float, default=0.05, help="Próg ciszy (0-1)")
    parser.add_argument("--silence-duration", type=float, default=0.3, help="Wymagana długość ciszy (s)")
    
    args = parser.parse_args()
    
    process_video(args.input_video, args.output_video, 
                 args.threshold, args.min_duration, args.max_duration,
                 args.silence_threshold, args.silence_duration)

# Dodaj dźwięk zakończenia
    import winsound
    winsound.Beep(1000, 500)  # Sygnał o częstotliwości 1000Hz trwający 500ms

if __name__ == "__main__":
    main()