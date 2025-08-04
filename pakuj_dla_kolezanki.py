#!/usr/bin/env python3
"""
Skrypt do pakowania Video Translation Studio dla koleżanki
"""
import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def main():
    print("📦 Pakowanie Video Translation Studio dla koleżanki...")
    print("=" * 60)
    
    # Sprawdź czy plik .exe istnieje
    exe_path = Path("dist/Video_Translation_Studio.exe")
    if not exe_path.exists():
        print("❌ Nie znaleziono pliku Video_Translation_Studio.exe!")
        print("Uruchom najpierw build_exe.py aby utworzyć plik .exe")
        return 1
    
    # Sprawdź czy folder intro_outro istnieje
    intro_outro_path = Path("intro_outro")
    if not intro_outro_path.exists():
        print("❌ Nie znaleziono folderu intro_outro!")
        return 1
    
    # Utwórz folder tymczasowy
    temp_dir = Path("temp_package")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    
    print("📁 Tworzę pakiet...")
    
    try:
        # Skopiuj plik .exe
        shutil.copy2(exe_path, temp_dir / "Video_Translation_Studio.exe")
        print("✅ Skopiowano Video_Translation_Studio.exe")
        
        # Skopiuj folder intro_outro
        shutil.copytree(intro_outro_path, temp_dir / "intro_outro")
        print("✅ Skopiowano folder intro_outro")
        
        # Skopiuj instrukcję
        instruction_path = Path("INSTRUKCJA_DLA_KOLEZANKI.txt")
        if instruction_path.exists():
            shutil.copy2(instruction_path, temp_dir / "INSTRUKCJA.txt")
            print("✅ Skopiowano instrukcję")
        
        # Utwórz plik ZIP
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"Video_Translation_Studio_{timestamp}.zip"
        zip_path = Path(zip_name)
        
        print(f"📦 Tworzę archiwum {zip_name}...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_dir)
                    zipf.write(file_path, arcname)
                    print(f"  📄 Dodano: {arcname}")
        
        # Sprawdź rozmiar
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"✅ Pakiet utworzony: {zip_path}")
        print(f"📏 Rozmiar: {zip_size_mb:.1f} MB")
        
        # Wyczyść folder tymczasowy
        shutil.rmtree(temp_dir)
        print("🗑️ Usunięto folder tymczasowy")
        
        print("\n🎉 Pakiet gotowy do wysłania!")
        print(f"📁 Plik: {zip_path.absolute()}")
        print("\n📤 Możesz teraz wysłać ten plik ZIP koleżance.")
        print("📖 W pakiecie znajduje się:")
        print("   - Video_Translation_Studio.exe")
        print("   - Folder intro_outro/ z plikami intro i outro")
        print("   - INSTRUKCJA.txt")
        
        return 0
        
    except Exception as e:
        print(f"❌ Błąd podczas pakowania: {e}")
        # Wyczyść folder tymczasowy w przypadku błędu
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 