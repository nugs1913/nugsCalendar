
@echo off
timeout /t 2 /nobreak > nul

:: 현재 디렉토리의 이전 파일들 삭제 (exe 파일 제외)
for %%i in ("c:\code\py\venv\Scripts\*") do (
    if not "%%~nxi"=="python.exe" (
        if not "%%~nxi"=="update.bat" (
            del "%%i" /q
        )
    )
)

:: 임시 디렉토리의 모든 파일을 현재 디렉토리로 복사
xcopy "temp_update\*" "c:\code\py\venv\Scripts" /E /Y

:: 임시 디렉토리 삭제
rmdir "temp_update" /S /Q

:: 프로그램 재시작
start "" "c:\code\py\venv\Scripts\python.exe"

:: 배치 파일 자신을 삭제
del "%~f0"
            