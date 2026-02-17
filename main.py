#!/usr/bin/env python3
"""Fathom webhook - simplest working version"""
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'version': '1.0'})

@app.route('/webhook/fathom', methods=['POST'])
def webhook():
    data = request.json or {}
    print(f"Received: {data.get('event', 'unknown')} - {data.get('title', 'no title')}")
    return jsonify({'status': 'received'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
