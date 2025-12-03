from flask import Flask
import threading
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def health():
    return 'OK', 200

@app.route('/health')
def health_check():
    return 'Healthy', 200

# Start the Slack bot in a background thread
def start_bot():
    subprocess.run(['python', 'main.py'])

if __name__ == '__main__':
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Flask listens on port 8080 for Cloud Run
    app.run(host='0.0.0.0', port=8080, debug=False)
```

4. At the bottom, click **"Commit new file"**

**Step 3: Edit `requirements.txt`**

1. Click on `requirements.txt` in your repo
2. Click the **pencil icon** (Edit)
3. Replace the contents with:
```
slack-bolt==1.18.0
anthropic>=0.30.0
httpx>=0.25.0
python-dotenv==1.0.0
flask==2.3.0
