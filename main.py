import sys, os, json, datetime
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class TransparentWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.config_file = 'config.json'
        self.click_count = 0
        self.moving = False
        self.x = None
        self.y = None

        now = datetime.datetime.now()
        self.year = now.year
        self.month = now.month

        self.nomal = QFont('나눔스퀘어 네오', 12, QFont.Bold)
        self.small = QFont('나눔스퀘어 네오', 9)
        self.big = QFont('나눔스퀘어 네오', 20, QFont.Bold)

        self.setting = {
            "blank": "background-color: rgba(0, 0, 0, 0); color: black;",
            "day": "background-color: white; color: black; width: 120px; height: 120px;",
            "title": "background-color: black; color: white; border: 1px solid black;",
            "titleBtn": "background-color: black; color: white; border-radius: 25px; border: 1px solid black;",
            "dayTitle": "background-color: white; color: black; border: 1px solid black;",
            "todayTitle": "background-color: blue; color: white; border: 1px solid black;",
            "sundayTitle": "background-color: white; color: red; border: 1px solid black;",
            "saturdayTitle": "background-color: white; color: blue; border: 1px solid black;",
            "innerFrame": "background-color: white; color: black; width: 120px; height: 80px;"
        }

        self.initUI()
        self.load_window_position()

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, 940, 1140)

        self.showFrame()

    def showFrame(self):
        self.mousePressEvent = self.handle_click
        self.mouseReleaseEvent = self.stop_move
        self.mouseMoveEvent = self.do_move

        frame = QWidget(self)
        frame.setGeometry(0, 200, 940, 1140)
        frame.setStyleSheet(self.setting['blank'])

        title = QWidget(frame)
        title.setGeometry(0, 0, 940, 100)
        title.setStyleSheet(self.setting['blank'])
        title.setalinment = Qt.AlignCenter

        self.titleLabel = QLabel(f'{self.year}- {str(self.month).zfill(2)}', title)
        self.titleLabel.setGeometry(100, 0, 640, 100)
        self.titleLabel.setStyleSheet(self.setting['title'])
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.titleLabel.setFont(self.big)

        prevMonth = QLabel('◀', title)
        prevMonth.setGeometry(25, 25, 50, 50)
        prevMonth.setStyleSheet(self.setting['titleBtn'] + 'padding-right: 4px;')
        prevMonth.setAlignment(Qt.AlignCenter)
        prevMonth.setFont(self.big)
        prevMonth.mousePressEvent = self.prev_month

        nextMonth = QLabel('▶', title)
        nextMonth.setGeometry(765, 25, 50, 50)
        nextMonth.setStyleSheet(self.setting['titleBtn'] + 'padding-left: 4px;')
        nextMonth.setAlignment(Qt.AlignCenter)
        nextMonth.setFont(self.big)
        nextMonth.mousePressEvent = self.next_month

        self.dayFrames = {}
        for item in range(0, 42):
            dayFrame = QWidget(frame)
            dayFrame.setGeometry((item % 7) * 120, (item // 7) * 120 + 100, 120, 120)
            dayFrame.setStyleSheet(self.setting['day'])

            label = QLabel(f'{item}', dayFrame)
            label.setGeometry(0, 0, 120, 30)
            label.setAlignment(Qt.AlignCenter)
            label.setFont(self.nomal)

            if item % 7 == 0:
                label.setStyleSheet(self.setting['sundayTitle'])
            elif item % 7 == 6:
                label.setStyleSheet(self.setting['saturdayTitle'])
            else:
                label.setStyleSheet(self.setting['dayTitle'])

            innerFrame = QWidget(dayFrame)
            innerFrame.setGeometry(0, 30, 120, 80)
            innerFrame.setStyleSheet(self.setting['innerFrame'])

            self.dayFrames[f'dayFrame{item}'] = dayFrame
            setattr(dayFrame, 'label', label)

        # self.dayFrames['dayFrame1'].label.setStyleSheet(self.setting['sundayTitle'])

    def prev_month(self, e):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1

        self.titleLabel.setText(f'{self.year}- {str(self.month).zfill(2)}')
    
    def next_month(self, e):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1

        self.titleLabel.setText(f'{self.year}- {str(self.month).zfill(2)}')

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
                'height': self.height()
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
            'height': height
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        
        # 프로그램 종료
        self.close()

    def load_window_position(self):
        # 설정 파일이 존재하는 경우 위치 불러오기
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    x = config.get('x', 100)
                    y = config.get('y', 100)
                    width = config.get('width', 500)
                    height = config.get('height', 500)
                    
                    # 창 크기와 위치 설정
                    self.setGeometry(x, y, width, height)
            except json.JSONDecodeError:
                # 파일 읽기 실패 시 기본 위치로 설정
                self.setGeometry(100, 100, 500, 500)
        else:
            # 설정 파일 없을 때 기본 위치로 설정
            self.setGeometry(100, 100, 500, 500)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TransparentWindow()
    window.show()

    app.aboutToQuit.connect(window.on_closing)
    sys.exit(app.exec_())