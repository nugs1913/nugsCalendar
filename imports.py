import sys, os, json, calendar, time, subprocess, requests, zipfile, shutil
from datetime import datetime, timedelta, date
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, 
                               QDateTimeEdit, QPushButton, QGridLayout, 
                               QVBoxLayout, QHBoxLayout, QMessageBox, 
                               QProgressDialog)
from PySide6.QtCore import Qt, QTimer, QTime, QDateTime
from PySide6.QtGui import QFont, QFontDatabase
from packaging import version

from functools import partial
from enum import Enum
from dataclasses import dataclass

from win10toast import ToastNotifier
from pystray import Icon, Menu, MenuItem
from PIL import Image
import win32com.client
from win32com.client import Dispatch

import logging

if os.path.exists('app.log'):
    os.remove('app.log')

logging.basicConfig(filename='app.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Google API 관련 라이브러리
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request