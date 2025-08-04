@echo off
echo 🎬 Uruchamianie Video Translation Studio...
echo.

REM Sprawdź czy istnieje środowisko wirtualne
if exist "myenv\Scripts\activate.bat" (
    echo 📦 Aktywuję środowisko wirtualne...
    call myenv\Scripts\activate.bat
    
    REM Przejdź do folderu z kodem
    cd code
    
    REM Uruchom aplikację
    echo 🚀 Uruchamiam aplikację...
    python video_translation_app.py
) else (
    echo ⚠️  Nie znaleziono środowiska wirtualnego. Uruchamiam z systemowym Pythonem...
    
    REM Przejdź do folderu z kodem
    cd code
    
    REM Uruchom aplikację
    echo 🚀 Uruchamiam aplikację...
    python video_translation_app.py
)

REM Pauza na końcu (opcjonalnie)
echo.
echo ✅ Aplikacja została zamknięta.
pause 