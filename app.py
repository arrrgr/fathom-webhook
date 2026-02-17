#!/usr/bin/env python3
"""
Fathom AI → Slack Webhook (Flask + Gunicorn)
"""
import os
import json
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID', 'GA7RW1JuxjdE4uHdkj1NDQ')
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL', '')

processed_calls = set()

def post_to_slack(title, call_id, date, duration, participants, transcript):
    """Post to Slack using webhook URL"""
    if not SLACK_WEBHOOK_URL:
        print(f"   ⚠️ No SLACK_WEBHOOK_URL configured")
        return True
    
    payload = {
        "channel": SLACK_CHANNEL_ID,
        "text": f"📞 *{title}*\nID: `{call_id}` | {duration//60} min | {', '.join(participants) if participants else 'N/A'}"
    }
    
    try:
        import requests
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload)
        return resp.status_code == 200
    except Exception as e:
        print(f"   ❌ Slack error: {e}")
        return False

@app.route('/webhook/fathom', methods=['POST'])
def fathom_webhook():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No payload'}), 400
        
        if data.get('event') != 'call.completed':
            return jsonify({'status': 'ignored'}), 200
        
        call_id = data.get('call_id')
        if call_id in processed_calls:
            return jsonify({'status': 'duplicate'}), 200
        
        processed_calls.add(call_id)
        
        title = data.get('title', 'Unknown')
        date = data.get('date', 'N/A')[:10]
        duration = data.get('duration_seconds', 0)
        participants = data.get('participants', [])
        transcript = data.get('transcript', '')
        
        print(f"\n📞 FATHOM WEBHOOK RECEIVED")
        print(f"   Call: {title}")
        print(f"   ID: {call_id}")
        print(f"   Date: {date} | Duration: {duration//60} min")
        print(f"   Participants: {', '.join(participants)}")
        print(f"   Transcript: {len(transcript)} chars")
        
        # Post to Slack
        success = post_to_slack(title, call_id, date, duration, participants, transcript)
        if success:
            print(f"   ✅ Posted to Slack #{SLACK_CHANNEL_ID}")
        else:
            print(f"   ⚠️ Slack post failed (no webhook URL?)")
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'processed_calls': len(processed_calls)
    })

@app.route('/webhook/slack', methods=['POST'])
def slack_webhook():
    """Handle Slack interactive messages"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
# Updated: Tue Feb 17 04:25:23 UTC 2026
