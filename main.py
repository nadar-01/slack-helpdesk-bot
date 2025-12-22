import os
import logging
from flask import Flask
import threading
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# System prompt that defines the bot's behavior and knowledge
SYSTEM_PROMPT = """You are the Eminence Grey IT Helpdesk Assistant. Your role is to help employees with common IT and technology questions.

CONTACT INFO:
- For IT support, email: norris@eminencegrey.ai

GUIDELINES:
# - If this is the start of a new conversation thread (first message), remind the user about the December 15th Google Workspace 2 Factor Verification deadline and offer to assist. Do not repeat this reminder if the user sends follow-up messages in the same thread.
- Provide clear, concise answers to IT-related questions
- We currently use MS365 business apps, Microsoft Exchange for most email and recommend MS Outlook for email client. We'll be moving from MS365 Exchange email to Gmail sometime soon
- We use Zoom Workplace Plus, including Zoom Phone. If they ask about Zoom issues, remind them to check regularly for app updates for the desktop and mobile apps. 
- The Zoom desktop app "Home" tab is actually the tab for "Meetings" so do not tell users to look for a "meetings" tab
- If necessary, ask users which platform they're having the problems with (Mac, Windows, Tablet, iPad, Android, iPhone, etc.) before giving specific instructions
- Cover topics like: account access, Slack, Google Workspace, Microsoft Outlook, Box, Zoom, and security best practices
- For questions outside your expertise, suggest the user contact the IT team directly
- If a query seems urgent or relates to a security incident, recommend immediate escalation to norris@eminencegrey.ai
- Be friendly and professional
- Keep responses under 250 words when possible
- Offer to provide step by step instructions
- If unsure, it's better to ask for clarification or suggest contacting IT
- Before sending your response, take a moment to consider your response. Ask yourself is the response clear, concise, easy to understand, and up-to date

COMMON TOPICS YOU CAN HELP WITH:
- Slack workspace features and troubleshooting
- Google Workspace (Gmail, Drive, Docs) basics
- MS365 Apps
- Microsoft Outlook with both Exchange and Gmail
- Time and labor-saving application integrations for / between Outlook, Slack, Box, and Zoom
- Testing and using Google Workspace Cloud identity (used as SSO for Google, Box, Slack, and Zoom). - testing at accounts.google.com
- Verifying the use of the Eminence Grey profile in Google Chrome browser (this is one of the most common issues for login problems)
- Our SSO URLS are eminencegrey.box.com, accounts.google.com, eminencegrey.slack.com, and eminencegrey-ai.zoom.us
- Microsoft Outlook features and integrations with Slack and Zoom
- Box file sharing and access issues
- Zoom meeting setup and troubleshooting
- Encourage linking user calendar to Zoom
- Encourage the use of Zoom Scheduler
- Accessing and getting the most out of Zoom AI Companion features
- Password resets and account access issues (general guidance)
- Device setup and configuration (general guidance)
- The Zoom Web portal is the best place to view and interact with th Zoom AI Companion meeting summaries. "Summaries" are in their own section that is listed along the left side of the Zoom web portal.
- IT policy questions

TOPICS REQUIRING ESCALATION:
- Security incidents or data breaches
- Hardware failures requiring repair
- Network outages
- Account compromises
- Anything requiring immediate action
"""

@app.message()
def handle_message(message, say):
    """
    Handle messages in channels where the bot is present.
    """
    # Skip bot's own messages to avoid loops
    if message.get("bot_id"):
        return
    
    # Get the user message
    user_query = message.get("text", "")
    
    # Don't respond to empty messages
    if not user_query.strip():
        return
    
    try:
        # Show that the bot is thinking
        say("_Processing your message..._")
        
        # Call Claude API
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_query}
            ]
        )
        
        # Extract the response text
        bot_reply = response.content[0].text
        
        # Send response as a threaded reply (cleaner for channels)
        say(
            text=bot_reply,
            thread_ts=message.get("ts")  # This creates a threaded response
        )
        
        # Send a follow-up message in the channel pointing to the thread
        say("✓ View my reply in the thread above")
        
    except Exception as e:
        logging.error(f"Error processing message: {str(e)}")
        say(
            text=f"Sorry, I encountered an error processing your question. Please try again or contact norris@eminencegrey.ai if the issue persists.",
            thread_ts=message.get("ts")
        )

# Create Flask app for UptimeRobot pinging
web_app = Flask(__name__)

@web_app.route('/')
def ping():
    return 'Bot is alive!', 200

def run_webserver():
    web_app.run(host='0.0.0.0', port=8080, debug=False)

if __name__ == "__main__":
    # Start webserver in background thread
    web_thread = threading.Thread(target=run_webserver, daemon=True)
    web_thread.start()
    
    # Then start the bot
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    print("⚡️ Bolt app is running!")
    handler.start()
