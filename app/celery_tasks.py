from app import app, celery, Arduino
import time
import random

@celery.task(bind=True)
def say_hey():
    print "hey"
    time.sleep(3)
    print "hey again"
    return "Hey again returned"
