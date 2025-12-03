import subprocess
import threading
import time
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return 'OK', 200

def start_bot():
    subprocess.run(['python', 'main.py'])

if __name__ == '__main__':
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    time.sleep(1)
    app.run(host='0.0.0.0', port=8080)
