import sys, os, json, calendar, requests, xmltodict, schedule, time, threading
from datetime import datetime, timedelta, date
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from win10toast import ToastNotifier
from pystray import Icon, Menu, MenuItem
from PIL import Image

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

    def get_google_credentials(self):
        # OAuth 2.0 스코프 설정 (캘린더 읽기 권한)
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        
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
                    print(f"Token refresh error: {e}")
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
                    print(f"Authentication error: {e}")
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
                fields='items(summary,start/dateTime,end/dateTime)'
            ).execute()
            events = events_result.get('items', [])
        
            event_dict = {}
            for event in events:
                start = event.get('start', {}).get('dateTime')
                end = event.get('end', {}).get('dateTime')

                if start and end:
                    event_date = datetime.fromisoformat(start).date().isoformat()
                    if event_date not in event_dict:
                        event_dict[event_date] = []
                    event_dict[event_date].append({
                        "summary": event.get('summary'), 
                        "start": datetime.fromisoformat(start).time().isoformat(), 
                        "end": datetime.fromisoformat(end).time().isoformat()
                    })

            return event_dict
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def get_events(self):
        return self.get_calendar_events(
            datetime.combine(datetime.now(), datetime.min.time()),
            datetime.combine(datetime.now(), datetime.max.time())
        )

class Widget(QWidget):
    def __init__(self):
        super().__init__()

        self.config_file = 'config.json'
        self.click_count = 0
        self.moving = False
        self.x = None
        self.y = None

        now = datetime.now()
        self.year = now.year
        self.month = now.month
        self.cal = calendar.Calendar(calendar.MONDAY)

        today = date.today()
        self.today = today.isoformat()

        self.nomal = QFont('나눔스퀘어 네오', 12, QFont.Bold)
        self.small = QFont('나눔스퀘어 네오', 9)
        self.big = QFont('나눔스퀘어 네오', 20, QFont.Bold)

        self.setting = {
            "blank": "background-color: rgba(0, 0, 0, 0);",
            "day": "background-color: white; color: black; width: 120px; height: 120px;",
            "title": "background-color: rgba(0, 0, 0, 0); color: white;",
            "titleBtn": "background-color: white; color: black; border-radius: 15px; border: 1px solid black;",
            "dayTitle": "background-color: white; color: black; border: 1px solid black;",
            "todayTitle": "background-color: black; color: white; border: 1px solid black;",
            "tSundayTitle": "background-color: red; color: white; border: 1px solid black;",
            "tSaturdayTitle": "background-color: blue; color: white; border: 1px solid black;",
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

        self.titleLabel = QLabel(f'{self.year} - {str(self.month).zfill(2)}', title)
        self.titleLabel.setGeometry(100, 0, 640, 100)
        self.titleLabel.setStyleSheet(self.setting['title'])
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.titleLabel.setFont(self.big)

        prevMonth = QLabel('◀', title)
        prevMonth.setGeometry(125, 35, 30, 30)
        prevMonth.setStyleSheet(self.setting['titleBtn'] + 'padding-right: 3px;')
        prevMonth.setAlignment(Qt.AlignCenter)
        prevMonth.setFont(self.nomal)
        prevMonth.mousePressEvent = self.prev_month

        nextMonth = QLabel('▶', title)
        nextMonth.setGeometry(665, 35, 30, 30)
        nextMonth.setStyleSheet(self.setting['titleBtn'] + 'padding-left: 2px;')
        nextMonth.setAlignment(Qt.AlignCenter)
        nextMonth.setFont(self.nomal)
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

            innerFrame = QWidget(dayFrame)
            innerFrame.setGeometry(0, 30, 120, 80)
            innerFrame.setStyleSheet(self.setting['innerFrame'])

            innerLabel = QLabel('', innerFrame)
            innerLabel.setGeometry(0, 0, 120, 80)
            innerLabel.setFont(self.small)
            innerLabel.setWordWrap(True)
            innerLabel.setAlignment(Qt.AlignCenter)

            self.dayFrames[f'dayFrame{item}'] = dayFrame
            setattr(dayFrame, 'label', label)
            setattr(dayFrame, 'innerFrame', innerFrame)
            setattr(dayFrame, 'innerLabel', innerLabel)

        self.set_calendar()

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
        # 해당 월의 첫날 생성
        first_day = date(self.year, self.month, 1)
        
        # 해당 월의 마지막 날 계산
        _, last_day_of_month = calendar.monthrange(self.year, self.month)
        last_day = date(self.year, self.month, last_day_of_month)
        
        # 첫날의 요일 (0:월요일 ~ 6:일요일)
        weekday = 0 if first_day.weekday() == 6 else first_day.weekday()

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
            if idx < weekday or idx >= last_day_of_month + weekday:
                day.setVisible(False)
                continue
            else:
                day.setVisible(True)

                current_date = date(self.year, self.month, idx - weekday + 1).isoformat()
                day.label.setText(str(idx - weekday + 1))

                if idx % 7 == 0:
                    if self.today == current_date:
                        day.label.setStyleSheet(self.setting['tSundayTitle'])
                    else:
                        day.label.setStyleSheet(self.setting['sundayTitle'])
                elif idx % 7 == 6:
                    if self.today == current_date:
                        day.label.setStyleSheet(self.setting['tSaturdayTitle'])
                    else:
                        day.label.setStyleSheet(self.setting['saturdayTitle'])
                else:
                    if self.today == current_date:
                        day.label.setStyleSheet(self.setting['todayTitle'])
                    else:
                        day.label.setStyleSheet(self.setting['dayTitle'])
                
                # 해당 날짜의 이벤트 가져오기
                events = self.event_dict.get(current_date, [])
                event_text = ''
                if events:
                    event_texts = [f"{event['summary']}" for event in events]
                    event_text = "\n".join(event_texts)

                day.innerLabel.setText(event_text)

                # 해당 날짜가 휴일인 경우 sundayTitle 스타일 적용
                if current_date.replace('-', '') in holiday_dict:
                    if self.today == current_date:
                        day.label.setStyleSheet(self.setting['tSundayTitle'])
                    else:
                        day.label.setStyleSheet(self.setting['sundayTitle'])
                    day.innerLabel.setText(holiday_dict[current_date.replace('-', '')])

    def prev_month(self, e):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1

        self.set_calendar()
    
    def next_month(self, e):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1

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
        public.noti_events = public.get_calendar_events(
            datetime.combine(datetime.now(), datetime.min.time()),
            datetime.combine(datetime.now(), datetime.max.time())
        )
        window.set_calendar()
        self.reload_noti()
        
    def show_event_list(self):
        result = []
        for time, content in self.event_dict.items():
            result.append(f"{time} - {content}")
        content = " / ".join(result)

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
    schedule.every().day.at("00:00").do(window.set_calendar)

    # 스케줄러 스레드 시작
    schedule_thread = threading.Thread(target=run_schedule)
    schedule_thread.daemon = True
    schedule_thread.start()

    tray.tray_run()

    app.aboutToQuit.connect(window.on_closing)
    sys.exit(app.exec_())