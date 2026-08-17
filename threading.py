import time
from threading import Thread

def task():
    print("Task started...")
    time.sleep(2)
    print("Task finished!")

# Create and start the thread
t = Thread(target=task)
t.start()
t.join()
