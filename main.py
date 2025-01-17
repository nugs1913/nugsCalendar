from imports import *
import updater, googleapi

class Public:

    def __init__(self):
        self.toggle = False
        self.x = 100
        self.y = 100
        self.width = 900
        self.height = 900
        self.theme = 'light'

        self.auto_sync = True

        self.load_config()

    def load_config(self):
        config_path = 'config.json'
        version_path = './src/version.json'

        # config.json 처리
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.x = config.get('x', self.x)
                    self.y = config.get('y', self.y)
                    self.width = config.get('width', self.width)
                    self.height = config.get('height', self.height)
                    self.theme = config.get('theme', self.theme)
            except json.JSONDecodeError:
                logging.error('Error decoding config.json')
        else:
            logging.info('config.json not found. Using default values.')

        # version.json 처리
        if os.path.exists(version_path):
            try:
                with open(version_path, 'r') as f:
                    version = json.load(f)
                    self.version = version.get('version', '0.0.0')
            except json.JSONDecodeError:
                logging.error('Error decoding version.json')
                self.version = '0.0.0'
        else:
            logging.info('version.json not found. Creating default file.')
            self.version = '0.0.0'
            os.makedirs(os.path.dirname(version_path), exist_ok=True)
            with open(version_path, 'w') as f:
                json.dump({'version': self.version}, f)

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
                /* 기본 스타일 */
                .blank {{
                    background-color: rgba(0, 0, 0, 0);
                }}

                .title {{
                    background-color: rgba(0, 0, 0, 0);
                    color: {white};
                    margin-bottom: 30px;
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

                .borderBottom {{
                    border-bottom: 1px solid {gray};
                    padding-bottom: 2px;
                }}

                /* 버튼 스타일 */
                .titleBtn {{
                    background-color: rgba(0, 0, 0, 0);
                    color: {white};
                    margin-bottom: 30px;
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
                    padding-left: 10px;
                    padding-right: 10px;
                    padding-top: 10px;
                    color: {white};
                }}

                .detailLabel{{
                    color: {white};
                }}

                .holidayLabel {{
                    color: red;
                }}

                .anniversaryLabel {{
                    color: #32CD32;
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
        self.x = public.x
        self.y = public.y

        self.detailFrame = None

        now = datetime.now()
        self.year = now.year
        self.month = now.month
        self.cal = calendar.Calendar(calendar.MONDAY)

        # .ttf 파일 로드
        font_path = "./src/NanumSquareNeo-bRg.ttf"  # ttf 파일 경로
        font_id = QFontDatabase.addApplicationFont(font_path)  # 글꼴 등록
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]  # 글꼴 이름 가져오기

        self.big = QFont(font_family, 20, QFont.Bold)
        self.nomal = QFont(font_family, 12, QFont.Bold)
        self.small = QFont(font_family, 10)
        self.smaller = QFont(font_family, 8)

        self.set_theme(Theme(public.theme))
        self.initUI()

    def set_theme(self, theme: Theme):
        self.theme_manager.set_theme(theme)
        self.update_stylesheet()

        x = self.x
        y = self.y

        # 변경된 테마 저장
        config = {
            'x': x,
            'y': y,
            'width': public.width,
            'height': public.height,
            'theme': self.theme_manager.current_theme.value
        }
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
    
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
        cell_height = 130  # 원하는 셀 높이
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
            innerLabel.setAlignment(Qt.AlignHCenter)
            
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

    def set_calendar(self):
        logging.debug('set_calendar called')

        # 해당 월의 첫날 생성
        first_day = date(self.year, self.month, 1)
        
        # 해당 월의 마지막 날 계산
        _, last_day_of_month = calendar.monthrange(self.year, self.month)
        last_day = date(self.year, self.month, last_day_of_month)
        
        # 첫날의 요일 (0:월요일 ~ 6:일요일)
        weekday = -1 if first_day.weekday() == 6 else first_day.weekday()

        # try:
        #     url = 'http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo'
        #     params ={'serviceKey' : 'FS3S0m+2dg9Sj8RC7nAmYT9mFoFhZL33RGaDdWBkVjjP9c4rpqIJqtRofnqpwo7J9GKEzsGiJm2nTqSpxBsaxw=='
        #             , 'solYear' : self.year
        #             , 'solMonth' : str(self.month).zfill(2) }

        #     response = requests.get(url, params=params)
        #     # 바이트 데이터를 UTF-8로 디코딩
        #     decoded_xml = response.content.decode('utf-8')

        #     # XML을 Python 딕셔너리로 변환
        #     xml_dict = xmltodict.parse(decoded_xml)

        #     # dateName과 locdate를 추출하여 딕셔너리 생성
        #     holiday_dict = {}
        #     try:
        #         items = xml_dict.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        #     except AttributeError:
        #         items = []

        #     # items가 리스트가 아닌 경우 리스트로 변환
        #     if isinstance(items, dict):
        #         items = [items]
        # except Exception as e:
        #     logging.error(f'Error in load holiday: {e}')

        # for item in items:
        #     locdate = item.get('locdate')
        #     dateName = item.get('dateName')
        #     if locdate and dateName:
        #         holiday_dict[locdate] = dateName 휴일 구글에서 가져오고 있음 나중에 음력 넣고 싶으면 사용

        # 날짜 범위를 사용하여 이벤트 가져오기
        self.event_dict, holiday_dict = api.get_calendar_events_and_holidays(
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
                if current_date in holiday_dict:
                    if holiday_dict[current_date].get('description') == '공휴일':
                        if today == current_date:
                            day.label.setProperty('class', 'tSundayTitle')
                        else:
                            day.label.setProperty('class', 'sundayTitle')

                        day.holidayLabel.setProperty('class', 'holidayLabel')
                    
                    else:
                        day.holidayLabel.setProperty('class', 'anniversaryLabel')

                    day.holidayLabel.setText(holiday_dict[current_date].get('summary'))

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
                
                # 기념일, 공휴일 구분을 위한 스타일 재지정
                day.holidayLabel.style().unpolish(day.holidayLabel)
                day.holidayLabel.style().polish(day.holidayLabel)
                day.holidayLabel.update()

    def show_detail(self, e, label):

        # 기존에 작성된 디테일창이 있으면 제거하고 다시 작성 
        if hasattr(self, 'detailFrame') and self.detailFrame is not None:
            self.detailFrame.deleteLater()
            self.detailFrame = None
        
        # 라벨의 실제 위치 계산
        global_pos = label.mapToGlobal(label.rect().topLeft())
        parent_pos = self.mapFromGlobal(global_pos)
        x = parent_pos.x() - 5 if parent_pos.x() + 375 < 840 else parent_pos.x() - 435
        y = parent_pos.y()

        self.detailFrame = QWidget(self)
        self.detailFrame.setGeometry(x + 130, min(y, 400), 300, 500)
        self.detailFrame.setProperty('class', 'detailFrame')

        detailLayout = QVBoxLayout()
        detailLayout.setContentsMargins(10, 20, 10, 0)  # 레이아웃 여백 제거
        detailLayout.setSpacing(5)
        detailLayout.setAlignment(Qt.AlignTop)
        self.detailFrame.setLayout(detailLayout)

        current_date = date(self.year, self.month, int(label.text())).isoformat()
        events = self.event_dict.get(current_date, [])

        event_texts = [f"{event['summary']}|{event['start']} ~ {event['end']}|{event['location']}" for event in events]
        
        dateLabel = QLabel(f'{current_date}', self.detailFrame) # 날짜 표시
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
            listLayout = QHBoxLayout()
            listLayout.setContentsMargins(0, 0, 0, 0)
            listLayout.setSpacing(10)

            container = QWidget(self.detailFrame)
            container.setLayout(listLayout)
            container.setFixedHeight(33)
            container.setProperty('class', 'borderBottom')
            detailLayout.addWidget(container)

            contentLayout = QVBoxLayout()
            contentLayout.setContentsMargins(0, 0, 0, 0)
            contentLayout.setSpacing(1)

            content = QWidget(self.detailFrame)
            content.setLayout(contentLayout)
            content.setFixedHeight(30)
            content.setCursor(Qt.PointingHandCursor)
            content.mousePressEvent = partial(self.show_event, event=text, current_date=current_date)
            listLayout.addWidget(content)

            contentLabel = QLabel(text.split("|")[0], self.detailFrame) #일정 내용
            contentLabel.setProperty('class', 'detailLabel')
            contentLabel.setFont(self.small)
            contentLabel.setWordWrap(True)
            contentLabel.setFixedWidth(220)  # 라벨 너비 고정

            contentTime = QLabel(text.split("|")[1], self.detailFrame) #일정 시간
            contentTime.setProperty('class', 'detailLabel')
            contentTime.setFont(self.smaller)
            contentTime.setWordWrap(True)
            contentTime.setFixedWidth(220)  # 라벨 너비 고정

            deleteBtn = QPushButton('삭제', self.detailFrame)
            deleteBtn.setFont(self.small)
            deleteBtn.clicked.connect(partial(self.delete_event, events[idx]['id'], label))
            deleteBtn.setCursor(Qt.PointingHandCursor)
            deleteBtn.setFixedSize(50, 30)  # 버튼 너비 고정

            contentLayout.addWidget(contentLabel)
            contentLayout.addWidget(contentTime)
            listLayout.addWidget(deleteBtn)
        
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
        inputContentLabel.setProperty('class', 'detailLabel')
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
        inputStartLabel.setProperty('class', 'detailLabel')
        inputStartLabel.setFont(self.small)
        inputStartLabel.setFixedWidth(50)

        inputStart = QDateTimeEdit(self.detailFrame)
        inputStartLayout.addWidget(inputStart)
        inputStart.setFont(self.small)
        inputStart.setDisplayFormat('yyyy-MM-dd / HH:mm')
        inputStart.setDateTime(datetime.strptime(current_date, '%Y-%m-%d'))
        inputStart.dateTimeChanged.connect(
            lambda:(
                inputEnd.setMinimumDateTime(inputStart.dateTime().addSecs(60)),
                inputEnd.setDateTime(inputStart.dateTime().addSecs(3600))
            )
        )
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
        inputEndLabel.setProperty('class', 'detailLabel')
        inputEndLabel.setFont(self.small)
        inputEndLabel.setFixedWidth(50)

        inputEnd = QDateTimeEdit(self.detailFrame)
        inputEndLayout.addWidget(inputEnd)
        inputEnd.setFont(self.small)
        inputEnd.setDisplayFormat('yyyy-MM-dd / HH:mm')
        inputEnd.setDateTime(datetime.strptime(current_date, '%Y-%m-%d') + timedelta(hours=1))
        inputEnd.setFixedWidth(220)

        inputLocationLayout = QHBoxLayout()
        inputLocationLayout.setContentsMargins(0, 0, 0, 0)
        inputLocationLayout.setSpacing(10)

        inputLocationContainer = QWidget(self.detailFrame)
        inputLocationContainer.setLayout(inputLocationLayout)
        inputLocationContainer.setFixedHeight(30)
        detailLayout.addWidget(inputLocationContainer)

        inputLocationLabel = QLabel('장소', self.detailFrame)
        inputLocationLayout.addWidget(inputLocationLabel)
        inputLocationLabel.setProperty('class', 'detailLabel')
        inputLocationLabel.setFont(self.small)
        inputLocationLabel.setFixedWidth(50)

        inputLocation = QLineEdit(self.detailFrame)
        inputLocationLayout.addWidget(inputLocation)
        inputLocation.setFont(self.small)
        inputLocation.setPlaceholderText('장소를 입력하세요')
        inputLocation.setFixedWidth(220)

        addBtn = QPushButton('추가', self.detailFrame)
        detailLayout.addWidget(addBtn)
        addBtn.setFont(self.small)
        addBtn.clicked.connect(lambda: self.add_event(
            str(inputContent.text()), 
            inputStart.dateTime(), 
            inputEnd.dateTime(), 
            str(inputLocation.text()), 
            label
        ))
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
        widget.deleteLater() #요소 삭제하고
        self.detailFrame = None #None으로 없에기 

    def show_event(self, e, event, current_date):
        #일정 자세히 보기
        self.contentFrame = QWidget(self.detailFrame)
        self.contentFrame.setGeometry(0, 0, 300, 500)
        self.contentFrame.setProperty('class', 'detailFrame')

        self.contentDetailLayout = QVBoxLayout()
        self.contentDetailLayout.setContentsMargins(10, 20, 10, 0)
        self.contentDetailLayout.setSpacing(5)
        self.contentDetailLayout.setAlignment(Qt.AlignTop)

        self.contentFrame.setLayout(self.contentDetailLayout)

        dateLabel2 = QLabel(f'{current_date}', self.contentFrame) #날짜 표시
        self.contentDetailLayout.addWidget(dateLabel2)
        dateLabel2.setProperty('class', 'innerLabel')
        dateLabel2.setFont(self.nomal)
        dateLabel2.setAlignment(Qt.AlignCenter)
        dateLabel2.setFixedHeight(30)

        blank2 = QLabel('', self.contentFrame)
        blank2.setFixedHeight(30)
        self.contentDetailLayout.addWidget(blank2)

        exitBtn = QLabel('X', self.contentFrame)
        exitBtn.setGeometry(274, 3, 25, 25)
        exitBtn.setProperty('class', 'exitBtn')
        exitBtn.setAlignment(Qt.AlignCenter)
        exitBtn.setFont(self.nomal)
        exitBtn.mousePressEvent = partial(self.event_close)
        exitBtn.setCursor(Qt.PointingHandCursor)

        summary = QLabel("일정 : " + event.split("|")[0], self.contentFrame)
        self.contentDetailLayout.addWidget(summary)
        summary.setFixedHeight(40)
        summary.setProperty('class', 'borderBottom')
        summary.setFont(self.nomal)

        time = QLabel("시간 : " + event.split("|")[1], self.contentFrame)
        self.contentDetailLayout.addWidget(time)
        time.setProperty('class', 'borderBottom')
        time.setFixedHeight(40)
        time.setFont(self.nomal)

        if event.split("|")[2]:
            location = QLabel("장소 : " + event.split("|")[2], self.contentFrame)
            self.contentDetailLayout.addWidget(location)
            location.setProperty('class', 'borderBottom')
            location.setFixedHeight(40)
            location.setFont(self.nomal)

        self.contentFrame.raise_() #맨 앞으로 가져와서
        self.contentFrame.show() #출력

    def event_close(self, e):
        self.contentFrame.setVisible(False) #안보이게 하고
        self.contentFrame = None #None으로 제거

    def add_event(self, summary, start, end, location, label):
        if not api.service:
            return

        event = {
            'summary': summary,
            'location': location,
            'start': {
                'dateTime': start.toString(Qt.ISODate),
                'timeZone': 'Asia/Seoul' #글로벌 대응 필요
            },
            'end': {
                'dateTime': end.toString(Qt.ISODate),
                'timeZone': 'Asia/Seoul' #글로벌 대응 필요 + 휴일쪽도
            }
        }

        try:
            api.service.events().insert(calendarId='primary', body=event).execute()
            self.set_calendar()
            self.show_detail(None, label)
        except Exception as e:
            logging.error(f"Error adding event: {e}")

    def delete_event(self, event_id, label):

        if not api.service:
            return

        try:
            api.service.events().delete(calendarId='primary', eventId=event_id).execute()
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
        self.x = event.position().x()
        self.y = event.position().y()

    def stop_move(self, event):
        self.moving = False
        self.x = None
        self.y = None

    def do_move(self, event):
        if self.moving and self.x is not None and self.y is not None:
            deltax = event.position().x() - self.x
            deltay = event.position().y() - self.y
            x = self.pos().x() + deltax
            y = self.pos().y() + deltay
            self.move(x, y)

            # 이동 중에도 위치 저장
            config = {
                'x': x,
                'y': y,
                'width': public.width,
                'height': public.height,
                'theme': self.theme_manager.current_theme.value
            }

            with open(self.config_file, 'w') as f:
                json.dump(config, f)

    def on_closing(self):
        # 현재 창 위치와 크기 저장
        x = self.pos().x()
        y = self.pos().y()
        width = public.width
        height = public.height
        
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

class Tray:

    def __init__(self):
        self.toaster = ToastNotifier()

        self.event_dict = api.get_events()
        self.noti_dict = {}

        # 아이콘 설정
        self.icon = Icon(
            "NugsCalendarNotifier",
            self.create_image(),
            menu=self.make_menu()
        )

        self.set_notification()

    def make_menu(self):
        return Menu(
            MenuItem("Check Event List", self.show_event_list),
            MenuItem("Reload Events", self.on_reload_event),
            Menu.SEPARATOR,  # 구분선 추가
            MenuItem("Theme Toggle", window.toggle_theme),
            Menu.SEPARATOR,  # 구분선 추가
            MenuItem("Exit", self.on_exit)
        )

    def send_notification(self, content):

        if type(content) == str:
            text = content
        else:
            text = []
            for t in content:
                text.append(t)
            
            text = ", ".join(text)

        self.toaster.show_toast(
            title="Nugs Calendar", 
            msg=text, 
            icon_path='./src/icon.ico', 
            duration=0, 
            threaded=True
            )

    def check_and_notify(self):
        try:
            now = datetime.now()
            logging.debug('check notification called')
            keys_to_delete = []
            if self.noti_dict != None:
                for event_time_str, summary in self.noti_dict.items():
                    event_time = datetime.strptime(event_time_str, "%H:%M:%S").time()
                    event_datetime = datetime.combine(now.date(), event_time)
                    
                    if event_datetime - timedelta(minutes=10) <= now and now <= event_datetime:
                        self.send_notification(summary)
                        keys_to_delete.append(event_time_str)

            for key in keys_to_delete:
                del self.noti_dict[key]
        except Exception as e:
            logging.error(f'Error in checking noti events: {e}')

    def set_notification(self):
        logging.debug('set notification called')

        try:
            for event in self.event_dict.values():
                for e in event:
                    start = e.get('start', {})
                    end = e.get('end', {})
                    if start and end:
                        start_time = start
                        if start_time not in self.noti_dict:
                            self.noti_dict[start_time] = []

                        self.noti_dict[start_time].append(e.get('summary', 'No Title'))
        except Exception as e:
            logging.error(f'Error in set noti events: {e}')
    
    def reload_noti(self):
        self.event_dict = api.get_events()
        self.noti_dict = {}
        self.set_notification()

    def on_exit(self, icon):
        icon.stop()
        window.on_closing()
        os._exit(0)

    def do_none(self):
        None

    def on_reload_event(self):
        logging.debug('reload called')

        try:
            window.set_calendar()
            self.reload_noti()
            self.send_notification('Reload Complete')
        except Exception as e:
            logging.error(f"Error in reload: {e}")

    def reload_by_sync(self):
        logging.debug('reload by sync called')
        try:
            window.set_calendar()
            self.reload_noti()
        except Exception as e:
            logging.error(f"Error in reload by sync: {e}")

    def show_event_list(self):
        result = []
        for time, content in self.event_dict.items():
            result.append(f"{time} - {content}")

        content = " / ".join(result) if len(result) else 'No Event in 24hours...'

        self.send_notification(content)

    def create_image(self):
        image = Image.open('./src/icon.ico')
        return image

    def tray_run(self):
        self.icon.run_detached()

def start_timers():
    # check_and_notify를 매 분 0초에 실행
    def schedule_check_and_notify():
        tray.check_and_notify()
        QTimer.singleShot(60000, schedule_check_and_notify)  # 매 1분마다 실행

    next_minute = QDateTime.currentDateTime().addSecs(60 - QTime.currentTime().second())
    QTimer.singleShot(next_minute.toMSecsSinceEpoch() - QDateTime.currentMSecsSinceEpoch(), schedule_check_and_notify)

    # set_calendar를 매일 00:00에 실행
    def schedule_set_calendar():
        tray.on_reload_event()
        QTimer.singleShot(86400000, schedule_set_calendar)  # 매일 00:00에 실행

    next_midnight = QDateTime.currentDateTime().addDays(1).toMSecsSinceEpoch() // 86400000 * 86400000
    QTimer.singleShot(next_midnight - QDateTime.currentMSecsSinceEpoch(), schedule_set_calendar)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    api = googleapi.google_api()
    public = Public()
    window = Widget()
    tray = Tray()

    update = updater.GitHubUpdater(public.version, parent=window)

    print("업데이트 확인 중...")
    release, new_version = update.check_for_updates()
    if release:
        # 새로운 창에서 진행 상황 표시
        QMessageBox.information(window, "업데이트 확인", "새로운 업데이트가 있습니다!")
        asset = release['assets'][0]  # 첫 번째 자산 선택
        if asset['name'].endswith('.zip'):
            if update.download_and_extract_update(asset['url'], asset['name']):
                QMessageBox.information(window, "업데이트 완료", "다운로드 및 압축 해제가 완료되었습니다.\n재시작 후 적용됩니다.")
                update.install_update()
                sys.exit()
        else:
            QMessageBox.warning(window, "오류", "다운로드 가능한 자산이 없습니다.")
    else:
        print("현재 최신 버전을 사용 중입니다.")
    
    window.show()

    if public.auto_sync:
        auto_sync = QTimer()
        auto_sync.timeout.connect(tray.reload_by_sync)
        auto_sync.start(600000)  # 10분마다 실행

    start_timers()
    tray.tray_run()

    app.aboutToQuit.connect(window.on_closing)
    sys.exit(app.exec())