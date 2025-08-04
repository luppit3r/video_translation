#!/usr/bin/env python3
"""
Skrypt do uruchamiania Video Translation Studio ze środowiskiem wirtualnym
"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    # Ścieżka do środowiska wirtualnego
    venv_python = Path(__file__).parent / "myenv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        print("[BLAD] Nie znaleziono środowiska wirtualnego!")
        print("Upewnij się, że folder 'myenv' istnieje w katalogu projektu.")
        return 1
    
    # Ścieżka do aplikacji
    app_path = Path(__file__).parent / "code" / "video_translation_app.py"
    
    if not app_path.exists():
        print("[BLAD] Nie znaleziono aplikacji!")
        print(f"Szukana ścieżka: {app_path}")
        return 1
    
    print("[START] Uruchamianie Video Translation Studio ze środowiskiem wirtualnym...")
    print(f"Python: {venv_python}")
    print(f"Aplikacja: {app_path}")
    print("-" * 50)
    
    try:
        # Uruchom aplikację
        result = subprocess.run([str(venv_python), str(app_path)], 
                              cwd=Path(__file__).parent)
        return result.returncode
    except KeyboardInterrupt:
        print("\n👋 Aplikacja została zatrzymana przez użytkownika.")
        return 0
    except Exception as e:
        print(f"[BLAD] Błąd podczas uruchamiania: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 