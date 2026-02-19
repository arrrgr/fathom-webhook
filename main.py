#!/usr/bin/env python3
"""
Fathom Webhook Server
Receives call transcripts from Fathom, analyzes with Anthropic, posts to Slack.
"""
import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import anthropic
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/fathom.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL = os.environ.get('SLACK_CHANNEL', 'C0AFMM60B96')

# Initialize clients
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

logger.info("Fathom Webhook v2.0 initialized")
logger.info(f"Port: 8080")
logger.info(f"Slack: {SLACK_CHANNEL}")
logger.info(f"Anthropic: {'OK' if anthropic_client else 'MISSING'}")


def analyze_transcript(transcript):
    """Analyze transcript using Anthropic."""
    if not anthropic_client:
        return {"summary": "No Anthropic API key configured", "action_items": [], "topics": []}

    try:
        prompt = f"""Analyze this call transcript and extract:
1. A brief summary (2-3 sentences)
2. Action items (as a list)
3. Key topics discussed (as a list)

Transcript:
{transcript}

Respond in JSON format:
{{"summary": "...", "action_items": ["..."], "topics": ["..."]}}"""

        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text
        # Strip markdown code block markers
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        result = json.loads(text)
        logger.info(f"Anthropic analysis complete: {len(result.get('action_items', []))} action items found")
        return result
    except Exception as e:
        logger.error(f"Anthropic analysis failed: {e}")
        return {"summary": f"Analysis failed: {str(e)}", "action_items": [], "topics": []}


def post_to_slack(call_info, analysis):
    """Post formatted results to Slack."""
    if not slack_client:
        logger.error("No Slack client configured")
        return False

    try:
        summary = analysis.get('summary', 'N/A')
        action_items = analysis.get('action_items', [])
        topics = analysis.get('topics', [])

        action_text = '\n'.join([f"• {item}" for item in action_items]) if action_items else 'None'
        topics_text = ', '.join(topics) if topics else 'None'

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"📞 {call_info.get('title', 'Call')}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Event:*\n{call_info.get('event', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Duration:*\n{call_info.get('duration_seconds', 0)}s"},
                    {"type": "mrkdwn", "text": f"*Participants:*\n{', '.join(call_info.get('participants', []))}"},
                    {"type": "mrkdwn", "text": f"*Call ID:*\n{call_info.get('call_id', 'N/A')}"}
                ]
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary*\n{summary}"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Action Items*\n{action_text}"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Topics*\n{topics_text}"}
            }
        ]

        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL,
            blocks=blocks,
            text=f"New call analyzed: {call_info.get('title', 'Call')}"
        )
        logger.info(f"Posted to Slack: {response['ts']}")
        return True
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        return False
    except Exception as e:
        logger.error(f"Slack posting failed: {e}")
        return False


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "anthropic_configured": bool(ANTHROPIC_API_KEY),
        "slack_configured": bool(SLACK_BOT_TOKEN)
    })


@app.route('/webhook/fathom', methods=['POST'])
def webhook():
    """Handle incoming Fathom webhook."""
    try:
        data = request.get_json()
        logger.info(f"Received webhook: {data.get('event', 'unknown')} - {data.get('call_id', 'no-id')}")

        if not data:
            return jsonify({"error": "No JSON body"}), 400

        # Extract transcript
        transcript = data.get('transcript', '')
        if not transcript:
            logger.warning("No transcript in payload")
            return jsonify({"error": "No transcript"}), 400

        # Analyze
        logger.info("Starting Anthropic analysis...")
        analysis = analyze_transcript(transcript)

        # Post to Slack
        logger.info("Posting to Slack...")
        success = post_to_slack(data, analysis)

        if success:
            return jsonify({"status": "processed", "analysis": analysis}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to post to Slack"}), 500

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
