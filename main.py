# -*- coding: utf-8 -*-
# その日の予定を取得
from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import requests
import json
from pytz import timezone

# その日外出する時間帯（start -> end）の最高気温と、その時間帯に雨が降るか判断
def get_weather(start,end):
    rain = False
    temps = []
    city_name = 'Tokyo'
    API_KEY = "dc76b2baaf0220b3ddedff0e7526d962"
    api = "http://api.openweathermap.org/data/2.5/forecast?q={city},jp&units=metric&lang=ja&APPID={key}"
    url = api.format(city=city_name, key=API_KEY)

    # 気象情報を取得
    response = requests.get(url).json()
    for item in response['list']:
        forecastDatetime = timezone('Asia/Tokyo').localize(datetime.datetime.fromtimestamp(item['dt']))
        weatherDescription = item['weather'][0]['description']
        temperature = item['main']['temp']
        # 今日の東京の天気のうち外出中の天気情報のみ(雨が降るか/最高気温)を取得
        if forecastDatetime.day == datetime.date.today().day:
            if forecastDatetime.hour >= start and forecastDatetime.hour <= end:
                if "雨" in weatherDescription:
                    rain = True
                temps.append(temperature)
    return max(temps), rain



# その日の外出時間帯と、スーツ用事ありorおしゃれ用事ありorカジュアルかを判断
def get_calender():
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    creds = None

    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # その日の外出時間を判断
    start_time = datetime.datetime.now().replace(hour=0,minute=0,second=0,microsecond=0).isoformat()
    start_time = start_time + ".000000+09:00"
    end_time = datetime.datetime.now().replace(hour=23,minute=59,second=59,microsecond=0).isoformat()
    end_time = end_time + ".000000+09:00"

    events_result = service.events().list(calendarId='primary', timeMin=start_time,
                                        timeMax=end_time, singleEvents=True,
                                        orderBy='startTime').execute()
    events = events_result.get('items', [])
    start_times = []
    end_times = []
    suits = False
    official = False
    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('time'))
        start = datetime.datetime.strptime(start, '%Y-%m-%dT%H:%M:%S+09:00')
        end = event['end'].get('dateTime', event['end'].get('date'))
        end = datetime.datetime.strptime(end, '%Y-%m-%dT%H:%M:%S+09:00')
        # カレンダーのイベントの色を元に用事の種類を判断
        if 'colorId' in event:
            if  event['colorId'] == "11":
                suits = True
            elif  event['colorId'] == "2":
                official = True
        start_times.append(start.hour)
        end_times.append(end.hour)
    day_start_time = min(start_times)
    day_start_time = (day_start_time // 3) * 3
    day_end_time = max(end_times)
    day_end_time = (day_end_time // 3) * 3
    
    return day_start_time,day_end_time,suits,official

day_start_time,day_end_time,suits,official = get_calender()
max_temp,rain = get_weather(day_start_time,day_end_time)

# 結果に応じてつけるLEDを変える
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BOARD)

# 傘のライトをつける
if rain == True:
    GPIO.setup(21,GPIO.OUT)
    GPIO.output(21,True)

# コートのライトをつける(LEDライト不足)
if max_temp < 12:
    # GPIO.setup(19,GPIO.OUT)
    # GPIO.output(19,True)
    print("LED増設します！")

# スーツのライトをつける
if suits == True:
    GPIO.setup(11,GPIO.OUT)
    GPIO.output(11,True)
else:
    # カジュアルパターン
    if suits == False and official == False:
        # Tシャツとジーパンのライトをつける
        if max_temp >=21:
            GPIO.setup(13,GPIO.OUT)
            GPIO.output(13,True)
            GPIO.setup(15,GPIO.OUT)
            GPIO.output(15,True)
        else:
            # 長袖(LED不足)とジーパンのライトをつける
            GPIO.setup(15,GPIO.OUT)
            GPIO.output(15,True)
            #GPIO.setup(23,GPIO.OUT)
            #GPIO.output(23,True)
    #おしゃれパターン
    if suits == False and official == True:
        if max_temp >=21:
            # おしゃれな半袖服とチノパンのライトをつける（LED不足）
            GPIO.setup(19,GPIO.OUT)
            GPIO.output(19,True)
            print("LED増設する")
        else:
            # おしゃれなYシャツとチノパンをつける（どちらもLED不足）
            # GPIO.setup(27,GPIO.OUT)
            # GPIO.output(27,True)
            print("LED増設する")

time.sleep(10.0)
GPIO.cleanup()
