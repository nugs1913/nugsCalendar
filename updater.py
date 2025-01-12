from imports import *

class GitHubUpdater:
    def __init__(self, current_version, parent=None):
        self.owner = 'nugs1913'
        self.repo = 'nugsCalendar'
        self.current_version = current_version
        self.github_api = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"
        self.headers = {
            'Authorization': 'token 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',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.temp_dir = "temp_update"
        self.parent = parent  # PySide6 위젯과 연결

    def check_for_updates(self):
        try:
            response = requests.get(self.github_api, headers=self.headers)
            response.raise_for_status()
            
            latest_release = response.json()
            latest_version = latest_release['tag_name'].lstrip('v')
            
            if version.parse(latest_version) > version.parse(self.current_version):
                self.new_version = latest_version
                return latest_release, latest_version
            return None, None
        except requests.exceptions.RequestException as e:
            print(f"업데이트 확인 중 오류 발생: {e}")
            return None, None

    def download_and_extract_update(self, asset_url, zip_filename):
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir)

            # 진행 상황 창 생성
            progress = QProgressDialog("업데이트 다운로드 중...", "취소", 0, 100, self.parent)
            progress.setWindowTitle("업데이트 진행")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            headers = self.headers.copy()
            headers['Accept'] = 'application/octet-stream'

            response = requests.get(asset_url, headers=headers, stream=True)
            response.raise_for_status()

            zip_path = os.path.join(self.temp_dir, zip_filename)
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(zip_path, 'wb') as file:
                for data in response.iter_content(1024):
                    file.write(data)
                    downloaded += len(data)
                    if total_size > 0:
                        progress.setValue(int((downloaded / total_size) * 100))
                        QApplication.processEvents()  # UI 업데이트

                    # 취소 버튼이 눌리면 다운로드 중단
                    if progress.wasCanceled():
                        raise Exception("다운로드가 취소되었습니다.")

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)

            os.remove(zip_path)
            progress.setValue(100)
            progress.close()
            return True

        except Exception as e:
            print(f"[오류] 다운로드/압축해제 중 예외 발생: {e}")
            return False

    def install_update(self):
        """업데이트 설치"""
        try:
            current_dir = os.path.dirname(sys.executable)
            current_exe = 'nugsCalendar.exe'
            
            # 업데이트 스크립트 생성
            update_script = f"""
@echo off
timeout /t 2 /nobreak > nul

:: 현재 디렉토리의 모든 파일 삭제
for %%i in ("{current_dir}\\*") do (
    if not "%%~nxi"=="update.bat" (
        del "%%i" /q
    )
)

:: 임시 디렉토리의 모든 파일을 현재 디렉토리로 복사
xcopy "{self.temp_dir}\\*" "{current_dir}" /E /Y

:: 임시 디렉토리 삭제
rmdir "{self.temp_dir}" /S /Q

:: 프로그램 재시작
start "" "{current_exe}"

:: 배치 파일 자신을 삭제
del "%~f0"
exit
"""
            
            with open('update.bat', 'w', encoding='utf-8') as f:
                f.write(update_script)
            
            # 배치 파일을 숨김 모드로 실행
            subprocess.Popen(
                ['cmd', '/c', 'update.bat'],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # 업데이트 후 새로운 버전 저장
            self.save_version(self.new_version)

            sys.exit()
            
        except Exception as e:
            print(f"설치 중 오류 발생: {e}")
            return False
        
    def save_version(version):

        config = {'versioin': version}

        with open('./src/version.json', 'w') as f:
            json.dump(config, f)

        return version
