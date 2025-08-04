import os
import sys
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass
import logging
from typing import Optional
import shutil
import json

# Klucze API z zmiennych środowiskowych
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')

@dataclass
class ProcessingState:
    translation_done: bool = False
    audio_generated: bool = False
    video_overlayed: bool = False
    silence_removed: bool = False
    final_processed: bool = False
    
    def save(self, path: Path):
        with open(path, 'w') as f:
            json.dump(self.__dict__, f)
    
    @classmethod
    def load(cls, path: Path) -> 'ProcessingState':
        if not path.exists():
            return cls()
        with open(path, 'r') as f:
            data = json.load(f)
            return cls(**data)

class VideoProcessor:
    def __init__(self, input_txt: str, input_video: str, resume: bool = False):
        self.txt_path = Path(input_txt)
        self.video_path = Path(input_video)
        self.base_dir = self.txt_path.parent.parent
        self.scripts_dir = Path(__file__).parent  # Ścieżka do katalogu ze skryptami
        self.setup_directories()
        self.setup_logging()
        
        # Stan procesu
        self.state_file = self.txt_path.parent / "process_state.json"
        self.state = ProcessingState.load(self.state_file) if resume else ProcessingState()

    def setup_directories(self):
        """Tworzy wymagane katalogi i definiuje ścieżki plików."""
        self.output_dir = self.base_dir / "output"
        self.generated_dir = self.base_dir / "generated"
        self.logs_dir = self.base_dir / "logs"
        
        for directory in [self.output_dir, self.generated_dir, self.logs_dir]:
            directory.mkdir(exist_ok=True, parents=True)
            
        # Definiowanie ścieżek plików wynikowych
        self.translated_txt = self.txt_path.parent / f"{self.txt_path.stem}-en.txt"
        self.synchronized_output = self.output_dir / f"{self.video_path.stem}_synchronized.mp4"
        self.final_output = self.output_dir / f"{self.video_path.stem}_synchronized_white-bottom.mp4"

    def setup_logging(self):
        """Konfiguruje logging do pliku i konsoli."""
        log_file = self.logs_dir / f"{self.video_path.stem}_processing.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def run_command(self, command: list, description: str, cwd: Path = None) -> subprocess.CompletedProcess:
        """Wykonuje komendę i loguje wyniki."""
        logging.info(f"Starting {description}")
        logging.debug(f"Command: {' '.join(command)}")
        
        # Przygotowanie środowiska
        env = os.environ.copy()
        env['OPENAI_API_KEY'] = OPENAI_API_KEY
        env['ELEVENLABS_API_KEY'] = ELEVENLABS_API_KEY
        
        # Ustawienie ścieżki do pakietów z virtualenv
        venv_site_packages = os.path.join(
            os.path.dirname(os.path.dirname(sys.executable)),
            'Lib',
            'site-packages'
        )
        env['PYTHONPATH'] = venv_site_packages
        
        logging.info(f"Using PYTHONPATH: {env['PYTHONPATH']}")
        
        # Dodajemy parametr cwd do subprocess.run
        result = subprocess.run(command, 
                              capture_output=True, 
                              text=True, 
                              env=env,
                              cwd=str(cwd) if cwd else None)
        
        if result.returncode != 0:
            logging.error(f"Error during {description}:")
            logging.error(result.stderr)
            raise Exception(f"Failed during {description}")
        
        logging.info(f"Completed {description}")
        return result

    def translate(self):
        """Wykonuje tłumaczenie tekstu."""
        if self.state.translation_done:
            logging.info("Translation already completed, skipping...")
            return
        
        self.run_command([
            "python", "code/translate.py",
            str(self.txt_path),
            str(self.translated_txt)
        ], "translation")
        
        self.state.translation_done = True
        self.state.save(self.state_file)

    def generate_audio(self):
        """Generuje pliki audio."""
        if self.state.audio_generated:
            logging.info("Audio generation already completed, skipping...")
            return
        
        # Ustaw katalog roboczy na katalog zawierający pliki źródłowe
        working_dir = self.txt_path.parent
        self.generated_dir = working_dir / "generated"
        
        # Konwertuj ścieżki na względne względem working_dir
        relative_txt = Path(self.translated_txt.name)  # tylko nazwa pliku
        relative_video = Path(self.video_path.name)    # tylko nazwa pliku
        
        # Użyj bezwzględnej ścieżki do skryptu
        generate_script = self.scripts_dir / "generate.py"
        
        self.run_command([
            "python", str(generate_script),
            str(relative_txt),
            str(relative_video)
        ], "audio generation", cwd=working_dir)
        
        self.state.audio_generated = True
        self.state.save(self.state_file)

    def overlay_video(self):
        """Nakłada audio na video."""
        if self.state.video_overlayed:
            logging.info("Video overlay already completed, skipping...")
            return
        
        working_dir = self.txt_path.parent
        self.output_dir = working_dir / "output"
        audio_dir = working_dir / "generated" / self.txt_path.stem
        
        # Użyj bezwzględnej ścieżki do skryptu
        overlay_script = self.scripts_dir / "overlay.py"
        
        self.run_command([
            "python", str(overlay_script),
            str(self.translated_txt),
            str(self.video_path),
            "--audio_dir", str(audio_dir)
        ], "video overlay", cwd=working_dir)
        
        self.state.video_overlayed = True
        self.state.save(self.state_file)

    def remove_silence(self):
        """Usuwa fragmenty ciszy używając ulepszonej wersji."""
        if self.state.silence_removed:
            logging.info("Silence removal already completed, skipping...")
            return
        
        working_dir = self.txt_path.parent
        self.output_dir = working_dir / "output"
        input_video = self.output_dir / f"{self.video_path.stem}_synchronized.mp4"
        output_video = self.output_dir / f"{self.video_path.stem}_synchronized_no_silence.mp4"
        
        # Użyj ulepszonej wersji delete_sm
        silence_script = self.scripts_dir / "delete_sm_improved.py"
        
        self.run_command([
            "python", str(silence_script),
            str(input_video),
            str(self.translated_txt),  # Plik z tłumaczeniem
            str(output_video),
            "--safety_margin", "2.0",
            "--min_gap_duration", "3.0"
        ], "improved silence removal", cwd=working_dir)
        
        self.state.silence_removed = True
        self.state.save(self.state_file)

    def process_final(self):
        """Dodaje logo i białe pole."""
        if self.state.final_processed:
            logging.info("Final processing already completed, skipping...")
            return
        
        working_dir = self.txt_path.parent
        self.output_dir = working_dir / "output"
        
        # Użyj wideo po usunięciu ciszy jeśli dostępne
        if self.state.silence_removed:
            input_video = self.output_dir / f"{self.video_path.stem}_synchronized_no_silence.mp4"
        else:
            input_video = self.output_dir / f"{self.video_path.stem}_synchronized.mp4"
            
        output_video = self.output_dir / f"{self.video_path.stem}_synchronized_white-bottom.mp4"
        
        # Użyj bezwzględnej ścieżki do skryptu
        logo_script = self.scripts_dir / "white-bottom-logo.py"
        
        self.run_command([
            "python", str(logo_script),
            str(input_video),
            str(output_video)
        ], "adding logo and white bottom", cwd=working_dir)
        
        self.state.final_processed = True
        self.state.save(self.state_file)

    def cleanup(self):
        """Opcjonalne czyszczenie plików tymczasowych."""
        if all([self.state.translation_done, self.state.audio_generated,
                self.state.video_overlayed, self.state.final_processed]):
            logging.info("Cleaning up temporary files...")
            if self.state_file.exists():
                self.state_file.unlink()

    def process(self):
        """Główna metoda przetwarzania."""
        try:
            self.translate()
            self.generate_audio()
            self.overlay_video()
            self.remove_silence()  # Dodaj usuwanie ciszy
            self.process_final()
            self.cleanup()
            logging.info(f"Processing completed successfully! Final output: {self.final_output}")
            return str(self.final_output)
        except Exception as e:
            logging.error(f"Error during processing: {str(e)}")
            raise

def main():
    parser = argparse.ArgumentParser(description='Process video with translation and overlay.')
    parser.add_argument('input_txt', help='Path to input text file')
    parser.add_argument('input_video', help='Path to input video file')
    parser.add_argument('--resume', action='store_true', help='Resume from last successful step')
    
    args = parser.parse_args()
    
    try:
        processor = VideoProcessor(args.input_txt, args.input_video, args.resume)
        processor.process()
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()