#!/usr/bin/env python3
"""
Skrypt do budowania pliku .exe z Video Translation Studio
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🔨 Budowanie Video Translation Studio...")
    print("=" * 50)
    
    # Sprawdź czy jesteśmy w odpowiednim katalogu
    if not Path("code/video_translation_app.py").exists():
        print("❌ Błąd: Nie znaleziono pliku code/video_translation_app.py")
        print("Upewnij się, że jesteś w głównym katalogu projektu.")
        return 1
    
    # Sprawdź czy PyInstaller jest zainstalowany
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} jest zainstalowany")
    except ImportError:
        print("❌ PyInstaller nie jest zainstalowany!")
        print("Zainstaluj go: pip install pyinstaller")
        return 1
    
    # Usuń poprzednie pliki build
    build_dirs = ["build", "dist"]
    for dir_name in build_dirs:
        if Path(dir_name).exists():
            print(f"🗑️ Usuwam poprzedni katalog {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Usuń poprzedni plik .spec jeśli istnieje
    spec_file = Path("video_translation_app.spec")
    if spec_file.exists():
        print("🗑️ Usuwam poprzedni plik .spec...")
        spec_file.unlink()
    
    print("\n📦 Tworzę plik wykonywalny...")
    print("To może potrwać kilka minut...")
    
    try:
        # Uruchom PyInstaller
        cmd = [
            "myenv/Scripts/pyinstaller.exe",
            "--onefile",  # Jeden plik .exe
            "--windowed",  # Bez okna konsoli
            "--name=Video_Translation_Studio",
            "--icon=logo.png",
                    "--add-data=video_translation_config.json;.",
        "--add-data=logo.png;.",
        "--add-data=requirements.txt;.",
        "--add-data=Readme;.",
        # "--add-data=intro_outro;intro_outro",  # Zakomentowane - brak plików
        "--add-data=code/add_intro_outro.py;.",
        "--add-data=code/delete_sm.py;.",
        "--add-data=code/delete_sm_improved.py;.",
        "--add-data=code/detect_polish_text.py;.",
        "--add-data=code/social_media_post.py;.",
        "--add-data=code/transcribe_api.py;.",
        "--add-data=code/transcribe_improved.py;.",
        "--add-data=code/translate.py;.",
        "--add-data=code/white-bottom-logo.py;.",
            "--hidden-import=tkinter",
            "--hidden-import=tkinter.ttk",
            "--hidden-import=tkinter.filedialog",
            "--hidden-import=tkinter.messagebox",
            "--hidden-import=tkinter.scrolledtext",
            "--hidden-import=moviepy",
            "--hidden-import=moviepy.editor",
            "--hidden-import=cv2",
            "--hidden-import=openai",
            "--hidden-import=whisper",
            "--hidden-import=deep_translator",
            "--hidden-import=ffmpeg",
            "--hidden-import=yt_dlp",
            "--hidden-import=psutil",
            "--hidden-import=tqdm",
            "code/video_translation_app.py"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Budowanie zakończone pomyślnie!")
            
            # Sprawdź czy plik .exe został utworzony
            exe_path = Path("dist/Video_Translation_Studio.exe")
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"📁 Plik .exe utworzony: {exe_path}")
                print(f"📏 Rozmiar: {size_mb:.1f} MB")
                print(f"📍 Lokalizacja: {exe_path.absolute()}")
                
                print("\n🎉 Aplikacja jest gotowa!")
                print("Możesz teraz uruchomić Video_Translation_Studio.exe")
                print("bez konieczności instalowania Pythona!")
                
                return 0
            else:
                print("❌ Plik .exe nie został utworzony!")
                return 1
        else:
            print("❌ Błąd podczas budowania!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return 1
            
    except Exception as e:
        print(f"❌ Wystąpił błąd: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 