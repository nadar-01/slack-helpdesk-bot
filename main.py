"""
Eminence Grey AI Helpdesk Bot - IMPROVED WITH CONTEXT
Powered by Claude API and Slack Bolt

This script monitors the #corp-it-helpdesk channel and responds to IT-related questions
using Claude's intelligence. IMPROVED: Now retains context within threaded conversations.

Requirements:
- slack-bolt
- anthropic
- python-dotenv

Installation:
pip install slack-bolt anthropic python-dotenv
"""

import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import anthropic

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# System prompt that guides Claude's behavior
SYSTEM_PROMPT = """You are the IT Helpdesk Assistant for Eminence Grey. Your role is to help employees with common IT and technology questions.

GUIDELINES:
- We currently use MS365 business apps, Microsoft Exchange for most email and recommend MS Outlook for email client. We'll be moving from MS365 Exchange email to Gmail sometime soon
- We use Zoom Workplace Plus, including Zoom Phone. If they ask about Zoom issues, remind them to check regularly for app updates for the desktop and mobile apps.
- The Zoom desktop and web interfaces have been recently updated (version 6.7.0 as of December 2025) with new left-side navigation. The interface has been streamlined, so some features may be in different locations than older instructions describe.
- For Zoom settings, direct users to: (1) Use the "Search settings" feature within Zoom's settings menu, or (2) Check Zoom's official support documentation at support.zoom.com. This is more reliable than specific step-by-step instructions since the interface may have recently changed.
- Web portal access: Users can access Zoom settings at eminencegrey-ai.zoom.us and look for their account settings in the left navigation menu
- The Zoom desktop app "Home" tab is actually the tab for "Meetings" so do not tell users to look for a "meetings" tab
- If necessary, ask users which platform they're having problems with (Mac, Windows, Tablet, iPad, Android, iPhone, Web browser, etc.) before giving specific instructions, as settings locations differ across platforms
- For questions outside your expertise, suggest the user contact norris@eminencegrey.ai directly
- If a query seems urgent or relates to a security incident, recommend immediate escalation to norris@eminencegrey.ai
- Be friendly and professional
- Keep responses under 200 words when possible
- Offer to provide step by step instructions when appropriate
- If unsure about current interface locations, ask for clarification, acknowledge the interface has recently changed, or suggest using Zoom's search feature or official support docs rather than guessing
- We have a Slack channel called "# vendor-incidents"(https://eminencegrey.slack.com/archives/C0A8FS2NQU8)that receives outage and incident information from most of our vendors. The user can check that Slack channel if you suspect a vendor-related incident or outage may be causing their issue
- Before sending any reply, take a moment to consider your response. Ask yourself: Is the response clear, concise, easy to understand, and up-to-date?

COMMON TOPICS YOU CAN HELP WITH:
- Account access and authentication (Slack, Google Workspace, Microsoft Outlook, Box, Zoom)
- Slack workspace features and troubleshooting
- Google Workspace (Gmail, Drive, Docs) basics
- MS365 Apps and Microsoft Outlook
- Microsoft Outlook with both Exchange and Gmail
- Time and labor-saving application integrations between Outlook, Slack, Box, and Zoom
- Google Workspace Cloud identity (used as SSO for Google, Box, Slack, and Zoom) - testing at accounts.google.com
- Verifying use of the Eminence Grey profile in Google Chrome browser (common login issue)
- Our SSO URLs: eminencegrey.box.com, accounts.google.com, eminencegrey.slack.com, eminencegrey-ai.zoom.us
- Microsoft Outlook features and integrations with Slack and Zoom
- Box file sharing and access issues
- Zoom meeting setup and troubleshooting
- Zoom AI Companion features and meeting summaries (accessible via eminencegrey-ai.zoom.us)
- Zoom Phone setup and best practices
- Zoom Scheduler and calendar integration
- Password resets and account access issues (general guidance)
- Device setup and configuration (general guidance)
- We recommend using a secure password application. We have a 1-Password corporate account available - ask norris@eminencegrey.ai for details
- IT policy questions
- Security best practices

TOPICS REQUIRING ESCALATION:
- Security incidents or data breaches
- Hardware failures requiring repair
- Network outages
- Account compromises
- Anything requiring immediate action
"""

def fetch_thread_history(client, channel_id, thread_ts):
    """
    Fetch all messages in a thread to provide context to Claude.
    Returns a list of messages in chronological order.
    """
    try:
        result = client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=100  # Fetch up to 100 messages in the thread
        )
        return result.get("messages", [])
    except Exception as e:
        logger.error(f"Error fetching thread history: {str(e)}")
        return []


def build_conversation_for_claude(thread_messages):
    """
    Convert Slack thread messages into a format Claude can understand.
    Filters out bot messages and structures the conversation chronologically.
    """
    messages = []
    
    for msg in thread_messages:
        # Skip bot messages to avoid confusion
        if msg.get("bot_id"):
            continue
        
        # Determine if it's the user or the bot
        username = msg.get("username", "User")
        text = msg.get("text", "")
        
        # Skip empty messages
        if not text.strip():
            continue
        
        # If this is a message from the helpdesk bot itself, mark it as assistant
        # Otherwise, it's from a user
        if "helpdesk" in username.lower() or msg.get("app_id"):
            role = "assistant"
        else:
            role = "user"
        
        messages.append({
            "role": role,
            "content": text
        })
    
    return messages


@app.message()
def handle_message(message, say, client):
    """
    Handle messages in channels where the bot is present.
    Now includes thread context for multi-turn conversations.
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
        
        # Check if this is a threaded message (reply to a previous message)
        thread_ts = message.get("thread_ts") or message.get("ts")
        channel_id = message.get("channel")
        
        # Fetch thread history if this is a threaded conversation
        conversation_messages = []
        if message.get("thread_ts"):
            thread_messages = fetch_thread_history(client, channel_id, thread_ts)
            conversation_messages = build_conversation_for_claude(thread_messages)
        else:
            # If it's not a threaded message yet, just use the current message
            conversation_messages = [
                {"role": "user", "content": user_query}
            ]
        
        # Call Claude API with conversation context
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=conversation_messages
        )
        
        # Extract the response text
        bot_reply = response.content[0].text
        
        # Send response as a threaded reply (cleaner for channels)
        say(
            text=bot_reply,
            thread_ts=thread_ts  # This creates a threaded response
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        say(
            text=f"Sorry, I encountered an error processing your question. Please try again or contact norris@eminencegrey.ai if the issue persists.",
            thread_ts=message.get("thread_ts") or message.get("ts")
        )


if __name__ == "__main__":
    # Start the bot using Socket Mode
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    logger.info("⚡️ Eminence Grey Helpdesk Bot (with context) is running!")
    handler.start()
