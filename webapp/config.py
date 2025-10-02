import os

class Config:
    DB_HOST = 'localhost'
    DB_USER = 'root'
    DB_PASSWORD = 'sWo9kuH%YQ2dqcE'
    DB_NAME = 'digital_signatures'
    SECRET_KEY = os.urandom(24)