import sys, os, json, calendar, requests, xmltodict, schedule, time, threading
from datetime import datetime, timedelta, date
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QDateTimeEdit, QPushButton, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from functools import partial

from enum import Enum
from dataclasses import dataclass

from win10toast import ToastNotifier
from pystray import Icon, Menu, MenuItem
from PIL import Image

import logging

logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.basicConfig(filename='error.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Google API 관련 라이브러리
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

class Public:

    def __init__(self):
        # Google Calendar 인증 및 서비스 설정
        self.creds = self.get_google_credentials()
        
        # Google Calendar 서비스 생성
        if self.creds:
            self.service = build('calendar', 'v3', credentials=self.creds)
        else:
            self.service = None

        self.noti_events = self.get_events()

        self.toggle = False
        self.x = 100
        self.y = 100
        self.width = 940
        self.height = 940
        self.theme = 'light'

        self.load_config()

    def load_config(self):
        # 설정 파일이 존재하는 경우 위치 불러오기
        if os.path.exists('config.json'):
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    self.x = config.get('x', 100)
                    self.y = config.get('y', 100)
                    self.width = config.get('width', 500)
                    self.height = config.get('height', 500)
                    self.theme = config.get('theme', 'dark')

            except json.JSONDecodeError:
                logging.error('Error in load config')
        else:
            pass

    def get_google_credentials(self):
        # OAuth 2.0 스코프 설정 (캘린더 읽기 권한)
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        creds = None
        # token.json 파일 확인 (이전 인증 토큰)
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # 토큰이 없거나 유효하지 않은 경우
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logging.error(f"Token refresh error: {e}")
                    creds = None
            
            # 새로운 인증 진행
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'client_secret.json',  # OAuth 클라이언트 설정 JSON 파일
                        SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    
                    # 토큰 저장
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logging.error(f"Authentication error: {e}")
                    return None
        
        return creds
    
    def get_calendar_events(self, start_date, end_date):
        if not self.service:
            return []

        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime',
                fields='items(id,summary,start/dateTime,end/dateTime, start/date, end/date)'
            ).execute()
            events = events_result.get('items', [])
        
            event_dict = {}
            for event in events:
                start = event.get('start', {}).get('dateTime') if event.get('start', {}).get('dateTime') else event.get('start', {}).get('date')
                end = event.get('end', {}).get('dateTime') if event.get('end', {}).get('dateTime') else event.get('end', {}).get('date')

                if start and end:
                    event_date = datetime.fromisoformat(start).date().isoformat()
                    if event_date not in event_dict:
                        event_dict[event_date] = []

                    event_dict[event_date].append({
                        "id": event.get('id'),
                        "summary": event.get('summary'), 
                        "start": datetime.fromisoformat(start).time().isoformat(), 
                        "end": datetime.fromisoformat(end).time().isoformat()
                    })

            return event_dict
        except Exception as e:
            logging.error(f"Error fetching events: {e}")
            return []

    def get_events(self):
        return self.get_calendar_events(
            datetime.combine(datetime.now(), datetime.min.time()),
            datetime.combine(datetime.now(), datetime.max.time())
        )

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
                highlight='#03346E',
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
                /* 기본 스타일 */
                .blank {{
                    background-color: rgba(0, 0, 0, 0);
                }}

                .title {{
                    background-color: rgba(0, 0, 0, 0);
                    color: {white};
                }}
                            
                .day {{
                    background-color: {black};
                }}

                .dayTitleFrame {{
                    background-color: {black};
                }}

                .innerFrame {{
                    background-color: {black};
                    color: {white};
                    width: 120px;
                    height: 90px;
                }}
                
                .innerFrame:hover {{
                    border: 1px solid {highlight};
                    background-color: {highlight};
                    border-top: 0px;
                }}

                .detailFrame {{
                    background-color: {black};
                    color: {white};
                    width: 500px;
                    height: 500px;
                    border-radius: 15px;
                    border: 1px solid {gray};
                }}

                /* 버튼 스타일 */
                .titleBtn {{
                    background-color: rgba(0, 0, 0, 0);
                    color: {white};
                }}

                .exitBtn {{
                    background-color: rgba(0, 0, 0, 0);
                    color: {white};
                }}

                /* 요일 타이틀 스타일 */
                .dayTitle {{
                    background-color: {black};
                    color: {white};
                    border: 0px;
                    padding-bottom: 2px;
                    border-bottom: 1px solid {gray};
                }}

                .sundayTitle {{
                    background-color: {black};
                    color: red;
                    border: 0px;
                    padding-bottom: 2px;
                    border-bottom: 1px solid {gray};
                }}

                .saturdayTitle {{
                    background-color: {black};
                    color: blue;
                    border: 0px;
                    padding-bottom: 2px;
                    border-bottom: 1px solid {gray};
                }}

                /* 오늘 날짜 타이틀 스타일 */
                .todayTitle {{
                    background-color: {white};
                    color: {black};
                    border: 1px solid {white};
                    padding-bottom: 2px;
                }}

                .tSundayTitle {{
                    background-color: red;
                    color: white;
                    border: 1px solid red;
                    padding-bottom: 2px;
                }}

                .tSaturdayTitle {{
                    background-color: blue;
                    color: white;
                    border: 1px solid blue;
                    padding-bottom: 2px;
                }}

                .innerLabel {{
                    color: {white};
                }}

                .holidayLabel {{
                    color: red;
                }}
            """.format(**colors)

    def add_custom_theme(self, color_scheme: ColorScheme):
        self.color_schemes[Theme.CUSTOM] = color_scheme

class Widget(QWidget):
    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager()

        self.config_file = 'config.json'
        self.click_count = 0
        self.moving = False
        self.x = None
        self.y = None

        self.detailFrame = None

        now = datetime.now()
        self.year = now.year
        self.month = now.month
        self.cal = calendar.Calendar(calendar.MONDAY)

        self.nomal = QFont('나눔스퀘어 네오', 11, QFont.Bold)
        self.small = QFont('나눔스퀘어 네오', 9)
        self.big = QFont('나눔스퀘어 네오', 20, QFont.Bold)

        self.set_theme(Theme(public.theme))
        self.initUI()

    def set_theme(self, theme: Theme):
        self.theme_manager.set_theme(theme)
        self.update_stylesheet()
    
    def update_stylesheet(self):
        self.setStyleSheet(self.theme_manager.get_stylesheet())
    
    def toggle_theme(self):
        # 테마 전환
        current = self.theme_manager.current_theme
        new_theme = Theme.LIGHT if current == Theme.DARK else Theme.DARK
        self.set_theme(new_theme)

    def initUI(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(public.x, public.y, public.width, public.height)

        self.showFrame()

    def showFrame(self):
        self.mousePressEvent = self.handle_click
        self.mouseReleaseEvent = self.stop_move
        self.mouseMoveEvent = self.do_move

        grid = QGridLayout()
        self.setLayout(grid)

        # 모든 열의 너비를 동일하게 설정
        cell_width = 120  # 원하는 셀 너비
        for column in range(7):
            grid.setColumnMinimumWidth(column, cell_width)
            grid.setColumnStretch(column, 1)  # 모든 열에 동일한 stretch factor 적용

        # 모든 행의 높이를 동일하게 설정
        cell_height = 120  # 원하는 셀 높이
        for row in range(1, 7):  # 1부터 시작하는 이유는 첫 번째 행이 요일 표시 줄일 경우
            grid.setRowMinimumHeight(row, cell_height)
            grid.setRowStretch(row, 1)  # 모든 행에 동일한 stretch factor 적용

        frame = QWidget(self)
        grid.addWidget(frame, 0, 0, 7, 7)
        frame.setGeometry(0, 0, 940, 1140)
        frame.setProperty('class', 'blank')

        title = QWidget(frame)
        grid.addWidget(title, 0, 0, 1, 7)
        title.setProperty('class', 'blank')

        self.titleLabel = QLabel(f'{self.year} - {str(self.month).zfill(2)}', title)
        grid.addWidget(self.titleLabel, 0, 1, 1, 5)
        self.titleLabel.setProperty('class', 'title')
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.titleLabel.setFont(self.big)

        prevMonth = QLabel('◀', title)
        grid.addWidget(prevMonth, 0, 0, 1, 1)
        prevMonth.setProperty('class', 'titleBtn')
        prevMonth.setAlignment(Qt.AlignCenter)
        prevMonth.setFont(self.nomal)
        prevMonth.mousePressEvent = self.prev_month

        nextMonth = QLabel('▶', title)
        grid.addWidget(nextMonth, 0, 6, 1, 1)
        nextMonth.setProperty('class', 'titleBtn')
        nextMonth.setAlignment(Qt.AlignCenter)
        nextMonth.setFont(self.nomal)
        nextMonth.mousePressEvent = self.next_month

        self.dayFrames = {}
        for item in range(0, 42):
            # 메인 dayFrame 생성 및 메인 그리드에 추가
            dayFrame = QWidget(frame)
            grid.addWidget(dayFrame, item // 7 + 1, item % 7)
            dayFrame.setProperty('class', 'day')
            
            # dayFrame의 내부 레이아웃 설정
            dayLayout = QVBoxLayout(dayFrame)
            dayLayout.setContentsMargins(0, 0, 0, 0)
            dayLayout.setSpacing(0)
            
            # titleFrame 생성 및 설정
            titleFrame = QWidget(dayFrame)
            titleFrame.setProperty('class', 'dayTitleFrame')
            titleFrame.setFixedHeight(30)  # 높이 고정
            
            # titleFrame 내부 레이아웃
            titleLayout = QHBoxLayout(titleFrame)
            titleLayout.setContentsMargins(0, 0, 0, 0)
            
            # 날짜 라벨
            label = QLabel(f'{item}', titleFrame)
            label.setProperty('class', 'dayTitle')
            label.setAlignment(Qt.AlignCenter)
            label.setFont(self.nomal)
            titleLayout.addWidget(label)
            
            # innerFrame 생성 및 설정
            innerFrame = QWidget(dayFrame)
            innerFrame.setProperty('class', 'innerFrame')
            
            # innerFrame 내부 레이아웃
            innerLayout = QVBoxLayout(innerFrame)
            innerLayout.setContentsMargins(0, 0, 0, 0)
            innerLayout.setSpacing(0)
            
            # 휴일 라벨
            holidayLabel = QLabel('', innerFrame)
            holidayLabel.setProperty('class', 'holidayLabel')
            holidayLabel.setAlignment(Qt.AlignCenter)
            holidayLabel.setFont(self.small)
            holidayLabel.setFixedHeight(20)  # 높이 고정
            
            # 내부 라벨
            innerLabel = QLabel('', innerFrame)
            innerLabel.setProperty('class', 'innerLabel')
            innerLabel.setFont(self.small)
            innerLabel.setWordWrap(True)
            innerLabel.setAlignment(Qt.AlignCenter)
            
            # innerFrame에 라벨들 추가
            innerLayout.addWidget(holidayLabel)
            innerLayout.addWidget(innerLabel)
            
            # 클릭 이벤트 설정
            innerFrame.mousePressEvent = partial(self.show_detail, label=label)
            
            # dayFrame에 titleFrame과 innerFrame 추가
            dayLayout.addWidget(titleFrame)
            dayLayout.addWidget(innerFrame)
            
            # 참조 저장
            self.dayFrames[f'dayFrame{item}'] = dayFrame
            setattr(dayFrame, 'label', label)
            setattr(dayFrame, 'innerFrame', innerFrame)
            setattr(dayFrame, 'innerLabel', innerLabel)
            setattr(dayFrame, 'holidayLabel', holidayLabel)

        self.set_calendar()

    def on_toggle(self, enabled):
        if enabled:
            self.toggle_theme()
        else:
            self.set_theme(Theme.DARK)

    def display_none(widget, hide=True):
        # 현재 StyleSheet 가져오기
        current_style = widget.styleSheet()
        
        # 'display: none' 속성을 추가 또는 제거한 새로운 StyleSheet 생성
        new_style = []
        for line in current_style.split(';'):
            if 'display' not in line:
                new_style.append(line)
        
        if hide:
            new_style.append('display: none')
    
        # 새로운 StyleSheet 설정
        widget.setStyleSheet(';'.join(new_style))

    def set_calendar(self):
        logging.debug('set_calendar called')
        # 해당 월의 첫날 생성
        first_day = date(self.year, self.month, 1)
        
        # 해당 월의 마지막 날 계산
        _, last_day_of_month = calendar.monthrange(self.year, self.month)
        last_day = date(self.year, self.month, last_day_of_month)
        
        # 첫날의 요일 (0:월요일 ~ 6:일요일)
        weekday = -1 if first_day.weekday() == 6 else first_day.weekday()

        try:
            url = 'http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo'
            params ={'serviceKey' : 'FS3S0m+2dg9Sj8RC7nAmYT9mFoFhZL33RGaDdWBkVjjP9c4rpqIJqtRofnqpwo7J9GKEzsGiJm2nTqSpxBsaxw=='
                    , 'solYear' : self.year
                    , 'solMonth' : str(self.month).zfill(2) }

            response = requests.get(url, params=params)
            # 바이트 데이터를 UTF-8로 디코딩
            decoded_xml = response.content.decode('utf-8')

            # XML을 Python 딕셔너리로 변환
            xml_dict = xmltodict.parse(decoded_xml)

            # dateName과 locdate를 추출하여 딕셔너리 생성
            holiday_dict = {}
            try:
                items = xml_dict.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            except AttributeError:
                items = []

            # items가 리스트가 아닌 경우 리스트로 변환
            if isinstance(items, dict):
                items = [items]
        except Exception as e:
            logging.error(f'Error in load holiday: {e}')

        for item in items:
            locdate = item.get('locdate')
            dateName = item.get('dateName')
            if locdate and dateName:
                holiday_dict[locdate] = dateName

        # 날짜 범위를 사용하여 이벤트 가져오기
        self.event_dict = public.get_calendar_events(
            datetime.combine(first_day, datetime.min.time()),
            datetime.combine(last_day, datetime.max.time())
        )

        # 달력에 날짜 표시
        for idx, day in enumerate(self.dayFrames.values()):
            if idx <= weekday or idx - weekday >= last_day_of_month + 1:
                day.setVisible(False)
                continue
            else:
                day.setVisible(True)

                current_date = date(self.year, self.month, idx - weekday).isoformat()
                today = date.today().isoformat()
                day.label.setText(str(idx - weekday))
                day.holidayLabel.setText('')

                if idx % 7 == 0:
                    if today == current_date:
                        day.label.setProperty('class', 'tSundayTitle')
                    else:
                        day.label.setProperty('class', 'sundayTitle')
                elif idx % 7 == 6:
                    if today == current_date:
                        day.label.setProperty('class', 'tSaturdayTitle')
                    else:
                        day.label.setProperty('class', 'saturdayTitle')
                else:
                    if today == current_date:
                        day.label.setProperty('class', 'todayTitle')
                    else:
                        day.label.setProperty('class', 'dayTitle')

                # 해당 날짜가 휴일인 경우 sundayTitle 스타일 적용
                if current_date.replace('-', '') in holiday_dict:
                    if today == current_date:
                        day.label.setProperty('class', 'tSundayTitle')
                    else:
                        day.label.setProperty('class', 'sundayTitle')

                    day.holidayLabel.setText(holiday_dict[current_date.replace('-', '')])

                # 해당 날짜의 이벤트 가져오기
                events = self.event_dict.get(current_date, [])
                event_text = ''
                if events:
                    event_texts = [f"{event['summary']}" for event in events]
                    event_text = "\n".join(event_texts)

                day.innerLabel.setText(event_text)

                # 스타일 다시 적용
                day.label.style().unpolish(day.label)
                day.label.style().polish(day.label)
                day.label.update()

    def show_detail(self, e, label):

        if hasattr(self, 'detailFrame') and self.detailFrame is not None:
            self.detailFrame.deleteLater()
            self.detailFrame = None
        
        # 라벨의 실제 위치 계산
        global_pos = label.mapToGlobal(label.rect().topLeft())
        parent_pos = self.mapFromGlobal(global_pos)
        x = parent_pos.x() if parent_pos.x() + 375 < 840 else parent_pos.x() - 435
        y = parent_pos.y()

        self.detailFrame = QWidget(self)
        self.detailFrame.setGeometry(x + 130, min(y, 400), 300, 500)
        self.detailFrame.setProperty('class', 'detailFrame')

        detailLayout = QVBoxLayout()
        detailLayout.setContentsMargins(10, 20, 10, 0)  # 레이아웃 여백 제거
        detailLayout.setSpacing(0)
        detailLayout.setAlignment(Qt.AlignTop)
        self.detailFrame.setLayout(detailLayout)

        current_date = date(self.year, self.month, int(label.text())).isoformat()
        events = self.event_dict.get(current_date, [])

        event_texts = [f"{event['summary']} ({event['start']} ~ {event['end']})" for event in events]
        
        dateLabel = QLabel(f'{current_date}', self.detailFrame) #날짜 표시
        detailLayout.addWidget(dateLabel)
        dateLabel.setProperty('class', 'innerLabel')
        dateLabel.setFont(self.nomal)
        dateLabel.setAlignment(Qt.AlignCenter)
        dateLabel.setFixedHeight(30)

        blank = QLabel('', self.detailFrame)
        blank.setFixedHeight(30)
        detailLayout.addWidget(blank)

        idx = -1
        for idx, text in enumerate(event_texts):           
            contentLayout = QHBoxLayout()
            contentLayout.setContentsMargins(0, 0, 0, 0)
            contentLayout.setSpacing(10)

            container = QWidget(self.detailFrame)
            container.setLayout(contentLayout)
            container.setFixedHeight(30)
            detailLayout.addWidget(container)

            contentLabel = QLabel(text, self.detailFrame) #일정 내용
            contentLabel.setProperty('class', 'innerLabel')
            contentLabel.setFont(self.small)
            contentLabel.setWordWrap(True)
            contentLabel.setText(text)
            contentLabel.setFixedWidth(220)  # 라벨 너비 고정

            deleteBtn = QPushButton('삭제', self.detailFrame)
            deleteBtn.setFont(self.small)
            deleteBtn.clicked.connect(partial(self.delete_event, events[idx]['id'], label))
            deleteBtn.setCursor(Qt.PointingHandCursor)
            deleteBtn.setFixedWidth(50)  # 버튼 너비 고정

            contentLayout.addWidget(contentLabel)
            contentLayout.addWidget(deleteBtn)
        
        if idx > -1:
            blank = QLabel('', self.detailFrame)
            blank.setFixedHeight(30)
            detailLayout.addWidget(blank)

        inputContentLayout = QHBoxLayout()
        inputContentLayout.setContentsMargins(0, 0, 0, 0)
        inputContentLayout.setSpacing(10)
        
        inputContentContainer = QWidget(self.detailFrame)
        inputContentContainer.setLayout(inputContentLayout)
        inputContentContainer.setFixedHeight(30)
        detailLayout.addWidget(inputContentContainer)

        inputContentLabel = QLabel('일정 추가', self.detailFrame)
        inputContentLayout.addWidget(inputContentLabel)
        inputContentLabel.setProperty('class', 'innerLabel')
        inputContentLabel.setFont(self.small)
        inputContentLabel.setFixedWidth(50)

        inputContent = QLineEdit(self.detailFrame)
        inputContentLayout.addWidget(inputContent)
        inputContent.setFont(self.small)
        inputContent.setPlaceholderText('일정을 입력하세요')
        inputContent.setFixedWidth(220)

        inputStartLayout = QHBoxLayout()
        inputStartLayout.setContentsMargins(0, 0, 0, 0)
        inputStartLayout.setSpacing(10)

        inputStartContainer = QWidget(self.detailFrame)
        inputStartContainer.setLayout(inputStartLayout)
        inputStartContainer.setFixedHeight(30)
        detailLayout.addWidget(inputStartContainer)

        inputStartLabel = QLabel('시작 시간', self.detailFrame)
        inputStartLayout.addWidget(inputStartLabel)
        inputStartLabel.setProperty('class', 'innerLabel')
        inputStartLabel.setFont(self.small)
        inputStartLabel.setFixedWidth(50)

        inputStart = QDateTimeEdit(self.detailFrame)
        inputStartLayout.addWidget(inputStart)
        inputStart.setFont(self.small)
        inputStart.setDisplayFormat('yyyy-MM-dd / HH:mm')
        inputStart.setDateTime(datetime.strptime(current_date, '%Y-%m-%d'))
        inputStart.setFixedWidth(220)

        inputEndLayout = QHBoxLayout()
        inputEndLayout.setContentsMargins(0, 0, 0, 0)
        inputEndLayout.setSpacing(10)

        inputEndContainer = QWidget(self.detailFrame)
        inputEndContainer.setLayout(inputEndLayout)
        inputEndContainer.setFixedHeight(30)
        detailLayout.addWidget(inputEndContainer)

        inputEndLabel = QLabel('종료 시간', self.detailFrame)
        inputEndLayout.addWidget(inputEndLabel)
        inputEndLabel.setProperty('class', 'innerLabel')
        inputEndLabel.setFont(self.small)
        inputEndLabel.setFixedWidth(50)

        inputEnd = QDateTimeEdit(self.detailFrame)
        inputEndLayout.addWidget(inputEnd)
        inputEnd.setFont(self.small)
        inputEnd.setDisplayFormat('yyyy-MM-dd / HH:mm')
        inputEnd.setDateTime(datetime.strptime(current_date, '%Y-%m-%d') + timedelta(minutes=10))
        inputEnd.setFixedWidth(220)

        addBtn = QPushButton('추가', self.detailFrame)
        detailLayout.addWidget(addBtn)
        addBtn.setFont(self.small)
        addBtn.clicked.connect(lambda: self.add_event(str(inputContent.text()), inputStart.dateTime(), inputEnd.dateTime(), label))

        exitBtn = QLabel('X', self.detailFrame)
        exitBtn.setGeometry(274, 3, 25, 25)
        exitBtn.setProperty('class', 'exitBtn')
        exitBtn.setAlignment(Qt.AlignCenter)
        exitBtn.setFont(self.nomal)
        exitBtn.mousePressEvent = partial(self.detail_close, widget=self.detailFrame)
        exitBtn.setCursor(Qt.PointingHandCursor)

        # 프레임을 최상단으로 올리기
        self.detailFrame.raise_()
        self.detailFrame.show()

    def detail_close(self, e, widget):
        widget.deleteLater()
        self.detailFrame = None

    def add_event(self, summary, start, end, label):
        if not public.service:
            return

        event = {
            'summary': summary,
            'start': {
                'dateTime': start.toString(Qt.ISODate),
                'timeZone': 'Asia/Seoul'
            },
            'end': {
                'dateTime': end.toString(Qt.ISODate),
                'timeZone': 'Asia/Seoul'
            }
        }

        try:
            public.service.events().insert(calendarId='primary', body=event).execute()
            self.set_calendar()
            self.show_detail(None, label)
        except Exception as e:
            logging.error(f"Error adding event: {e}")

    def delete_event(self, event_id, label):

        if not public.service:
            return

        try:
            public.service.events().delete(calendarId='primary', eventId=event_id).execute()
            self.set_calendar()
            self.show_detail(None, label)
        except Exception as e:
            logging.error(f"Error deleting event: {e}")

    def prev_month(self, e):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1

        self.titleLabel.setText(f'{self.year} - {str(self.month).zfill(2)}')
        self.set_calendar()
    
    def next_month(self, e):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1

        self.titleLabel.setText(f'{self.year} - {str(self.month).zfill(2)}')
        self.set_calendar()

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

class Tray:

    def __init__(self):
        self.toaster = ToastNotifier()

        self.event_dict = {}

        self.set_notification()

    def send_notification(self, content):
        self.toaster.show_toast(
            title="Nugs Calendar", 
            msg=content, 
            icon_path='icon.ico', 
            duration=0, 
            threaded=True
            )

    def check_and_notify(self):
        now = datetime.now()
        logging.debug('check notification called')
        keys_to_delete = []
        if self.event_dict != None:
            for event_time_str, summary in self.event_dict.items():
                event_time = datetime.strptime(event_time_str, "%H:%M:%S").time()
                event_datetime = datetime.combine(now.date(), event_time)
                if event_datetime - timedelta(minutes=10) <= now and now <= event_datetime:
                    self.send_notification(summary)
                    keys_to_delete.append(event_time_str)

        for key in keys_to_delete:
            del self.event_dict[key]

    def set_notification(self):
        logging.debug('set notification called')
        for event in public.noti_events.values():
            for e in event:
                start = e.get('start', {})
                end = e.get('end', {})
                if start and end:
                    start_time = start
                    self.event_dict[start_time] = e.get('summary', 'No Title')

    def reload_noti(self):
        public.noti_events = public.get_events()
        self.event_dict = {}
        self.set_notification()
        self.send_notification('Reload Complete')

    def on_exit(self, icon):
        icon.stop()
        os._exit(0)

    def do_none(self):
        None

    def on_reload_event(self):
        logging.debug('reload called')

        window.set_calendar()
        self.reload_noti()
        
    def show_event_list(self):
        result = []
        for time, content in self.event_dict.items():
            result.append(f"{time} - {content}")

        content = " / ".join(result) if len(result) else 'No Event Today...'

        self.send_notification(content)

    def create_image(self):
        image = Image.open('icon.ico')
        return image
    
    def tray_run(self):
        # 메뉴 설정
        menu = Menu(
            MenuItem("Check Event List", self.show_event_list),
            MenuItem("Reload Events", self.on_reload_event),
            MenuItem("Exit", self.on_exit)
        )

        # 아이콘 설정
        self.icon = Icon("NugsCalendarNotifier", self.create_image(), menu=menu)
        self.icon.run_detached()

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    public = Public()
    window = Widget()
    tray = Tray()

    window.show()

    schedule.every().minute.at(":00").do(tray.check_and_notify)
    schedule.every(10).minutes.do(window.set_calendar)
    schedule.every().day.at("00:00:01").do(window.set_calendar)

    # 스케줄러 스레드 시작
    schedule_thread = threading.Thread(target=run_schedule)
    schedule_thread.daemon = True
    schedule_thread.start()

    tray.tray_run()

    app.aboutToQuit.connect(window.on_closing)
    sys.exit(app.exec())