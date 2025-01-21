from imports import *
    
class google_api():
    def __init__(self):
        self.creds = self.get_google_credentials()
        
        # Google Calendar 서비스 생성
        if self.creds:
            self.service = build('calendar', 'v3', credentials=self.creds)
        else:
            self.service = None
    def create_table(self, date):
        con = sqlite3.connect('./src/schedule.db')
        cursor = con.cursor()
        date = 'd' + date.split("T")[0].replace('-', '')
        try:
            cursor.execute(f'create table if not exists {date} (id text primary key, summary text, startTime text, endTime text, description text, location text)')
            return True
        except Exception as e:
            logging.error(f"DB - create table error: {e}")
            return False
        finally:
            con.commit()
            con.close()
    
    def insert_event(self, eventId, date, summary, startTime, endTime, description, location):
        con = sqlite3.connect('./src/schedule.db')
        cursor = con.cursor()
        date = 'd' + date.split("T")[0].replace('-', '')

        try:
            cursor.execute(f"select count(*) from {date} where id=?", (eventId,))
            data = cursor.fetchone()[0]

            if data:
                cursor.execute(f"update {date} set id=?, summary=?, startTime=?, endTime=?, description=?, location=? where id=?",
                    (eventId, summary, startTime, endTime, description, location, eventId))
            else:
                cursor.execute(f"insert into {date} values (?, ?, ?, ?, ?, ?)", 
                    (eventId, summary, startTime, endTime, description, location))

            return True
        except Exception as e:
            logging.error(f"DB - insert event error: {e}")
            return False
        finally:
            con.commit()
            con.close()

    def delete_event(self, eventId, date):
        con = sqlite3.connect('./src/schedule.db')
        cursor = con.cursor()
        date = 'd' + date.split("T")[0].replace('-', '')

        try:
            cursor.execute(f"select count(*) from {date} where id=?", (eventId,))
            data = cursor.fetchone()[0]

            if data:
                cursor.execute(f"delete from {date} where id=?", (eventId,))
                cursor.execute(f"select count(*) from {date}")
                data = cursor.fetchone()[0]
                if data == 0:
                    cursor.execute(f"drop table {date}")

            return True
        except Exception as e:
            logging.error(f"DB - delete event error: {e}")
            return False
        finally:
            con.commit()
            con.close()

    def insert_month(self, date):
        con = sqlite3.connect('./src/schedule.db')
        cursor = con.cursor()
        date = 'm' + date.split("T")[0].replace('-', '')

        try:
            cursor.execute(f"create table if not exists {date} (checker integer primary key)")
            return True
        except Exception as e:
            logging.error(f"DB - insert month error: {e}")
            return False
        finally:
            con.commit()
            con.close()

    def check_month(self, date):
        con = sqlite3.connect('./src/schedule.db')
        cursor = con.cursor()
        date = 'm' + date.split("T")[0].replace('-', '')

        try:
            cursor.execute(f"select * from {date}")
            return True
        except Exception as e:
            logging.error(f"DB - check month error: {e}")
            return False
        finally:
            con.close()

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

    def get_calendar_events(self, start_date, end_date, get_range):
        logging.info(f"API  - Fetching events from {start_date} to {end_date}")

        if not self.service:
            # Google Calendar 인증 및 서비스 설정
            self.creds = self.get_google_credentials()
            
            # Google Calendar 서비스 생성
            if self.creds:
                self.service = build('calendar', 'v3', credentials=self.creds)
            else:
                self.service = None

        max_retries = 1
        if get_range == 'all':
            calendar_ids = ['primary', 'ko.south_korea#holiday@group.v.calendar.google.com']
            order_by = 'startTime'
        else:
            calendar_ids = ['primary']
            order_by = 'updated'

        for attempt in range(max_retries):
            try:
                events = []
                for calendar_id in calendar_ids:
                    events_result = self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=start_date.isoformat() + 'Z',
                        timeMax=end_date.isoformat() + 'Z',
                        singleEvents=True,
                        orderBy=order_by,
                        fields='items(id, summary, location, start/dateTime, end/dateTime, start/date, end/date, description)'
                    ).execute()
                    events.extend(events_result.get('items', []))
                
                for event in events:
                    start = event.get('start', {}).get('dateTime') if event.get('start', {}).get('dateTime') else event.get('start', {}).get('date')
                    end = event.get('end', {}).get('dateTime') if event.get('end', {}).get('dateTime') else (datetime.fromisoformat(event.get('end', {}).get('date')) - timedelta(days=1)).isoformat()
                    location = event.get('location', {}) if event.get('location', {}) else '-'
                    description = event.get('description', '') if event.get('description', '') else '-'

                    if start and end:
                        if description != "-": #공휴일, 기념일

                            self.create_table(start)
                            self.insert_event('holiday', start, event.get('summary'), start, end, description, '-')
                        else:
                            if datetime.fromisoformat(start).date() != datetime.fromisoformat(end).date(): #긴 일정
                                for long in self.date_range(start, end):
                                    self.create_table(long.isoformat())
                                    self.insert_event(event.get('id'),
                                                      long.isoformat(),
                                                      event.get('summary'),
                                                      datetime.fromisoformat(start).date().isoformat(),
                                                      datetime.fromisoformat(end).date().isoformat(),
                                                      '-',
                                                      location)
                            else: #일반 하루짜리 일정
                                event_date = datetime.fromisoformat(start).date().isoformat()
                                self.create_table(event_date)
                                self.insert_event(event.get('id'),
                                                  event_date,
                                                  event.get('summary'),
                                                  datetime.fromisoformat(start).isoformat(),
                                                  datetime.fromisoformat(end).isoformat(),
                                                  '-',
                                                  location)

            except Exception as e:
                logging.error(f"Error fetching events: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프

    def get_calendar_events_from_db(self, first, end):
        logging.info(f"DB   - Fetching events from {first} to {end}")

        event_dict = {}
        holiday_dict = {}

        con = sqlite3.connect('./src/schedule.db')
        cursor = con.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        tables = [item[0] for item in tables]

        try:
            for date in self.date_range(str(first), str(end)):
                table = 'd' + date.isoformat().replace('-', '')
                if date.isoformat().split('-')[2] == '01' and not self.check_month(date.isoformat()):
                    self.insert_month(date.isoformat())
                    self.get_calendar_events(
                        datetime.combine(first, datetime.min.time()),
                        datetime.combine(end, datetime.max.time()),
                        'all'
                    )

                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    tables = [item[0] for item in tables]

                if table in tables:
                    data = cursor.execute(f'select * from {table}')
                    data = data.fetchall()

                    for d in data:
                        eventId = d[0]
                        summary = d[1]
                        event_date = date.isoformat()
                        start = d[2]
                        end = d[3]
                        description = d[4]
                        location = d[5]

                        if eventId == "holiday":

                            if event_date not in holiday_dict:
                                holiday_dict[event_date] = {}

                            holiday_dict[event_date] = {
                                'summary': summary,
                                'description': description
                            }
                        else:
                            if event_date not in event_dict:
                                event_dict[event_date] = []

                            event_dict[event_date].append({
                                "id": eventId,
                                "summary": summary, 
                                "start": datetime.fromisoformat(start).time().isoformat(), 
                                "end": datetime.fromisoformat(end).time().isoformat(),
                                "location": location
                            })

            return event_dict, holiday_dict
        except Exception as e:
            logging.error(f"Error fetching events: {e}")
            return {}, {}

    def sync_300days(self):
        logging.info("Syncing 300 days of events")

        first = datetime.now().date() - timedelta(days=100)
        end = first + timedelta(days=400)

        self.get_calendar_events(
            datetime.combine(first, datetime.min.time()),
            datetime.combine(end, datetime.max.time()),
            'all'
        )

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

if __name__ == '__main__':
    api = google_api()