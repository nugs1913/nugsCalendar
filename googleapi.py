from imports import *
    
class google_api():
    def __init__(self):
        self.creds = self.get_google_credentials()
        
        # Google Calendar 서비스 생성
        if self.creds:
            self.service = build('calendar', 'v3', credentials=self.creds)
        else:
            self.service = None

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
                    if getattr(sys, 'frozen', False):
                        client_secret_path = os.path.join(sys._MEIPASS, 'client_secret.json')
                    else:
                        client_secret_path = 'client_secret.json'
                    

                    flow = InstalledAppFlow.from_client_secrets_file(
                        client_secret_path,  # OAuth 클라이언트 설정 JSON 파일
                        SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    
                    # 토큰 저장
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())

                    self.create_startup_shortcut()
                except Exception as e:
                    logging.error(f"Authentication error: {e}")
                    return None
        
        return creds

    def get_calendar_events_and_holidays(self, start_date, end_date):
        if not self.service:
            # Google Calendar 인증 및 서비스 설정
            self.creds = self.get_google_credentials()
            
            # Google Calendar 서비스 생성
            if self.creds:
                self.service = build('calendar', 'v3', credentials=self.creds)
            else:
                self.service = None

        max_retries = 3
        calendar_ids = ['primary', 'ko.south_korea#holiday@group.v.calendar.google.com']

        for attempt in range(max_retries):
            try:
                events = []
                for calendar_id in calendar_ids:
                    events_result = self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=start_date.isoformat() + 'Z',
                        timeMax=end_date.isoformat() + 'Z',
                        singleEvents=True,
                        orderBy='startTime',
                        fields='items(id, summary, location, start/dateTime, end/dateTime, start/date, end/date, description)'
                    ).execute()
                    events.extend(events_result.get('items', []))
                
                event_dict = {}
                holiday_dict = {}
                for event in events:
                    start = event.get('start', {}).get('dateTime') if event.get('start', {}).get('dateTime') else event.get('start', {}).get('date')
                    end = event.get('end', {}).get('dateTime') if event.get('end', {}).get('dateTime') else (datetime.fromisoformat(event.get('end', {}).get('date')) - timedelta(days=1)).isoformat()
                    location = event.get('location', {}) if event.get('location', {}) else ''
                    description = event.get('description', '') if event.get('description', '') else ''

                    if start and end:
                        if event.get('description', ''):
                            event_date = start

                            if event_date not in holiday_dict:
                                holiday_dict[event_date] = {}

                            holiday_dict[event_date] = {
                                'summary': event.get('summary'),
                                'description': description
                            }
                        else:
                            if datetime.fromisoformat(start).date() != datetime.fromisoformat(end).date():
                                for long in self.date_range(start, end):
                                    if long.isoformat() not in event_dict:
                                        event_dict[long.isoformat()] = []

                                    event_dict[long.isoformat()].append({
                                        "id": event.get('id'),
                                        "summary": event.get('summary'),
                                        "start": datetime.fromisoformat(start).date().isoformat(),
                                        "end": datetime.fromisoformat(end).date().isoformat(),
                                        "location": location
                                    })
                            else:
                                event_date = datetime.fromisoformat(start).date().isoformat()
                                if event_date not in event_dict:
                                    event_dict[event_date] = []

                                event_dict[event_date].append({
                                    "id": event.get('id'),
                                    "summary": event.get('summary'), 
                                    "start": datetime.fromisoformat(start).time().isoformat(), 
                                    "end": datetime.fromisoformat(end).time().isoformat(),
                                    "location": location
                                })

                return event_dict, holiday_dict
            except Exception as e:
                logging.error(f"Error fetching events: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프
                return {}, {}

    def get_events(self):
        if not self.service:
            # Google Calendar 인증 및 서비스 설정
            self.creds = self.get_google_credentials()
            
            # Google Calendar 서비스 생성
            if self.creds:
                self.service = build('calendar', 'v3', credentials=self.creds)
            else:
                self.service = None

        try:
            now = datetime.now()
            start_date = now - timedelta(hours=24)
            end_date = now + timedelta(hours=24)

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime',
                fields='items(summary,start/dateTime,end/dateTime)'
            ).execute()
            events = events_result.get('items', [])

            noti_dict = {}
            for event in events:
                start = event.get('start', {}).get('dateTime')
                end = event.get('end', {}).get('dateTime')

                if start and end:
                    event_date = start_date.date().isoformat()

                    if event_date not in noti_dict:
                        noti_dict[event_date] = []

                    noti_dict[event_date].append({
                        "summary": event.get('summary'), 
                        "start": datetime.fromisoformat(start).time().isoformat(), 
                        "end": datetime.fromisoformat(end).time().isoformat()
                    })

            return noti_dict

        except Exception as e:
            logging.error(f"Error fetching events: {e}")
            return []

    def date_range(self, start, end):
        date_list = []
        start_date = datetime.fromisoformat(start).date()
        end_date = datetime.fromisoformat(end).date()
        while start_date <= end_date:
            date_list.append(start_date)
            start_date += timedelta(days=1)

        return date_list
    
    def create_startup_shortcut(self):
        # 현재 실행 중인 파이썬 스크립트의 전체 경로
        script_path = os.path.abspath(sys.argv[0])
        
        # 현재 사용자의 시작프로그램 폴더 사용
        startup_folder = os.path.join(os.getenv('APPDATA'), f'Microsoft\Windows\Start Menu\Programs\Startup')
        
        # 폴더가 존재하는지 확인
        if not os.path.exists(startup_folder):
            print(f"경로를 찾을 수 없습니다: {startup_folder}")
            return
        
        # 바로가기 파일 이름 설정
        shortcut_path = os.path.join(startup_folder, "nugsCalendar.lnk")
        
        # Windows Shell 객체 생성
        shell = win32com.client.Dispatch("WScript.Shell")
        
        # 바로가기 파일 이름 설정
        shortcut_path = os.path.join(startup_folder, "nugsCalendar.lnk")
        
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = script_path
        shortcut.WorkingDirectory = os.path.dirname(script_path)
        shortcut.save()
        
        print(f"바로가기가 생성되었습니다: {shortcut_path}")
