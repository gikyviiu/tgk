import os

class Config:
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = '29242233'
    DB_NAME = 'digital_signatures'
    SECRET_KEY = os.urandom(24)