@echo off
echo 🎬 Uruchamianie Video Translation Studio...
echo.

REM Sprawdź czy plik .exe istnieje
if exist "dist\Video_Translation_Studio.exe" (
    echo ✅ Znaleziono aplikację!
    echo 🚀 Uruchamiam Video Translation Studio...
    echo.
    
    REM Uruchom aplikację
    start "" "dist\Video_Translation_Studio.exe"
    
    echo ✅ Aplikacja została uruchomiona!
    echo 📝 Sprawdź czy okno aplikacji się otworzyło.
    
) else (
    echo ❌ Nie znaleziono pliku Video_Translation_Studio.exe!
    echo 📁 Sprawdź czy plik znajduje się w folderze dist\
    echo 🔨 Jeśli nie ma pliku, uruchom build_exe.py aby go utworzyć
)

echo.
pause 