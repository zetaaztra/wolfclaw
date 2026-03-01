import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def post_to_slack(channel: str, message: str):
    """Post a message to a Slack channel using SLACK_BOT_TOKEN."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    
    if not token:
        return "SLACK_BOT_TOKEN environment variable not set. Please configure Slack integration."
        
    client = WebClient(token=token)
    
    try:
        response = client.chat_postMessage(
            channel=channel,
            text=message
        )
        return f"Successfully posted message to {channel} (ts: {response['ts']})"
    except SlackApiError as e:
        return f"Error posting to Slack: {e.response['error']}"

def read_slack_messages(channel: str, limit: int = 5):
    """Read recent messages from a Slack channel."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    
    if not token:
        return "SLACK_BOT_TOKEN environment variable not set."
        
    client = WebClient(token=token)
    
    try:
        response = client.conversations_history(channel=channel, limit=limit)
        messages = response.get("messages", [])
        
        if not messages:
            return f"No messages found in {channel}"
            
        output = []
        for msg in messages:
            user = msg.get("user", "System/Bot")
            text = msg.get("text", "")
            output.append(f"User {user}: {text}")
            
        return "\n---\n".join(output)
    except SlackApiError as e:
        return f"Error reading from Slack: {e.response['error']}"
