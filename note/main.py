import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
                             QHBoxLayout, QTextEdit)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextOption
import markdown, os, json, logging, re
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from xml.etree import ElementTree

from enum import Enum
from dataclasses import dataclass

if os.path.exists('app.log'):
    os.remove('app.log')

logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class Theme(Enum):
    DARK = "dark"
    LIGHT = "light"
    CUSTOM = "custom"

@dataclass
class ColorScheme:
    white: str
    black: str
    gray: str
    background: str
    highlight: str
    text: str

class ThemeManager:
    def __init__(self):
        self.current_theme = Theme.DARK
        self.color_schemes = {
            Theme.DARK: ColorScheme(
                white='#F5EFE7',
                black='#021526',
                gray='#F5EFE7',
                background='#1E1E1E',
                highlight='#03346E',
                text='#FFFFFF'
            ),
            Theme.LIGHT: ColorScheme(
                white='#021526',
                black='#F5EFE7',
                gray='#021526',
                highlight='#CBA35C',
                background='#FFFFFF',
                text='#000000'
            ),
            Theme.CUSTOM: ColorScheme(
                white='#E0E0E0',
                black='#121212',
                gray='#A0A0A0',
                highlight='#D8C4B6',
                background='#2D2D2D',
                text='#E0E0E0'
            )
        }
    
    def set_theme(self, theme: Theme):
        self.current_theme = theme
    
    def get_colors(self):
        return vars(self.color_schemes[self.current_theme])
    
    def get_stylesheet(self):
        colors = self.get_colors()
        return """
                .main{{
                    background-color: {black};
                    color: {white};
                }}
                .viewer{{
                    background-color: black;
                    color: {white};
                }}
                .titleBar{{
                    background-color: {black};
                    color: {white};
                    height: 50px;
                    border: 0px;
                    border-bottom: 1px solid {white};
                }}
            """.format(**colors)

    def add_custom_theme(self, color_scheme: ColorScheme):
        self.color_schemes[Theme.CUSTOM] = color_scheme

# 체크박스를 처리하기 위한 커스텀 확장 클래스
class CheckboxExtension(markdown.Extension):
    def extendMarkdown(self, md):
        # 체크박스 패턴 추가
        md.inlinePatterns.register(CheckboxPattern(r'\[([ xX])\]', md), 'checkbox', 175)

class CheckboxPattern(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        p = re.compile('\[([xX])\]')
        checked = p.match(m.string)
        checkbox = ElementTree.Element('input')
        checkbox.set('type', 'checkbox')
        if checked:
            checkbox.set('checked', 'checked')
        return checkbox

class NoteWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 크기 조절을 위한 마진 설정
        self.resize_margin = 5
        
        # 마우스 추적 활성화
        self.setMouseTracking(True)
        
        # 크기 조절 상태 변수들
        self.moving = False

        self.theme = 'dark'
        self.X = None
        self.Y = None
        self.Width = None
        self.Height = None
        self.click_count = 0
        self.config_file = './note/editor_config.json'

        self.original_text = ""

        self.load_config()
        self.theme_manager = ThemeManager()
        self.set_theme(Theme(self.theme))
        self.initUI()

    def load_config(self):
        # 설정 파일이 존재하는 경우 위치 불러오기
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    self.X = config.get('x', 100)
                    self.Y = config.get('y', 100)
                    self.Width = config.get('width', 500)
                    self.Height = config.get('height', 500)
                    self.theme = config.get('theme', 'dark')

            except json.JSONDecodeError:
                logging.error('Error in load config')
        else:
            pass

    def set_theme(self, theme: Theme):
        self.theme_manager.set_theme(theme)
        self.update_stylesheet()

        x = self.pos().x()
        y = self.pos().y()

        # 변경된 테마 저장
        config = {
            'x': x,
            'y': y,
            'width': self.width(),
            'height': self.height(),
            'theme': self.theme_manager.current_theme.value
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)

    def update_stylesheet(self):
        self.setStyleSheet(self.theme_manager.get_stylesheet())

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(self.X, self.Y, self.Width, self.Height)

        self.showFrame()

    def showFrame(self):
        self.mousePressEvent = self.handle_click
        self.mouseReleaseEvent = self.stop_move
        self.mouseMoveEvent = self.do_move

        # 메인 위젯 설정
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self.setLayout(layout)
        self.setProperty('class', 'main')

        titleBar = QWidget()
        titleLayout = QHBoxLayout()
        titleBar.setLayout(titleLayout)
        layout.addWidget(titleBar)
        titleBar.setProperty('class', 'titleBar')
        titleBar.setFixedHeight(30)

        self.editor = QTextEdit()
        layout.addWidget(self.editor)
        self.editor.setProperty('class', 'main')
        self.editor.installEventFilter(self)

        self.viewer = QWebEngineView()
        layout.addWidget(self.viewer)
        self.viewer.setProperty('class', 'viewer')
        self.viewer.installEventFilter(self)

        editBtn = QLabel('📝')
        titleLayout.addWidget(editBtn)
        editBtn.setCursor(Qt.PointingHandCursor)
        editBtn.setFixedWidth(30)
        editBtn.mousePressEvent = self.show_original_text

        try:
            with open('note.md', 'r', encoding='utf-8') as f:
                text = f.read()
                self.original_text = text
                self.editor.setPlainText(text)
                self.apply_markdown()
        except FileNotFoundError:
            pass

    def eventFilter(self, watched, event):

        # 포커스 상실 시
        if event.type() == event.Type.FocusOut and watched == self.editor:
            self.save_file()
            self.apply_markdown()
            
        return super().eventFilter(watched, event)
    
    def show_original_text(self, e=None):
        """마크다운 원본 텍스트 표시"""
        if not self.original_text:
            self.original_text = self.editor.toPlainText()
        self.editor.setPlainText(self.original_text)
        self.editor.setVisible(True)
        self.viewer.setVisible(False)
    
    def apply_markdown(self, e=None):
        """마크다운 렌더링 적용"""
        extensions = [
            CheckboxExtension(),
            TableExtension(),
            FencedCodeExtension(),
            'nl2br'  # 줄바꿈 유지
        ]

        self.original_text = self.editor.toPlainText()
         # 각 라인을 개별적으로 처리
        lines = self.original_text.split('\n')
        html_lines = []
        final_html = ""

        for line in lines:
            if line != "":  # 내용이 있는 라인
                html_lines.append(markdown.markdown(line, extensions=extensions))
            else:  # 빈 라인
                html_lines.append("<br>")
        
        html_lines.append("</body>")

        colors = self.theme_manager.get_colors()
        background_color = colors['black']
        text_color = colors['white']

        # HTML 콘텐츠 생성 (CSS 포함)
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: {background_color};
                    color: {text_color};
                    margin: 20px;
                    padding: 0;
                }}
                body::-webkit-scrollbar {{
                    width: 2px;
                }}
                body::-webkit-scrollbar-thumb {{
                    background: #444;
                }}
                body::-webkit-scrollbar-track {{
                    background: {background_color};
                }}
                p {{
                    font-size: 16px;
                    line-height: 1.5;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                }}
                table, th, td {{
                    border: 1px solid {text_color};
                }}
                th, td {{
                    padding: 8px;
                    text-align: left;
                }}
                input[type="checkbox"] {{
                    transform: scale(1.2);
                    margin-right: 10px;
                }}
                p:has(input[type="checkbox"]:checked) {{
                    text-decoration: line-through;
                    color: gray;
                }}
            </style>
        </head>
        <body>
            {''.join(html_lines)}
        </body>
        </html>
        """

        self.viewer.setHtml(html_template)
        self.editor.setVisible(False)
        self.viewer.setVisible(True)

    def save_file(self):
        with open('note.md', 'w', encoding='utf-8') as f:
            f.write(self.original_text)

    def handle_click(self, event):
        if event.button() == Qt.LeftButton:
            self.click_count += 1
            if self.click_count == 3:
                self.start_move(event)
                self.click_count = 0
            else:
                QTimer.singleShot(500, self.reset_click_count)

    def reset_click_count(self):
        self.click_count = 0

    def start_move(self, event):
        self.moving = True
        self.x = event.x()
        self.y = event.y()

    def stop_move(self, event):
        self.moving = False
        self.x = None
        self.y = None

    def do_move(self, event):
        if self.moving and self.x is not None and self.y is not None:
            deltax = event.x() - self.x
            deltay = event.y() - self.y
            x = self.pos().x() + deltax
            y = self.pos().y() + deltay
            self.move(x, y)

            # 이동 중에도 위치 저장
            config = {
                'x': x,
                'y': y,
                'width': self.width(),
                'height': self.height(),
                'theme': self.theme_manager.current_theme.value
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)

    def on_closing(self):
        # 현재 창 위치와 크기 저장
        x = self.pos().x()
        y = self.pos().y()
        width = self.width()
        height = self.height()
        
        # JSON 파일로 저장
        config = {
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'theme': self.theme_manager.current_theme.value
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        
        # 프로그램 종료
        self.close()

def handle_sigint(signal, frame):
    QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 기본 폰트 설정
    font = app.font()
    font.setPointSize(11)
    app.setFont(font)
    
    window = NoteWidget()
    app.aboutToQuit.connect(window.on_closing)

    window.show()
    sys.exit(app.exec())