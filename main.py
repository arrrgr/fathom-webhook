#!/usr/bin/env python3
"""Fathom webhook - no dependencies"""
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = int(os.environ.get('PORT', 8080))
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID', 'GA7RW1JuxjdE4uHdkj1NDQ')

processed_calls = set()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'healthy', 'version': '1.0'}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/webhook/fathom':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            try:
                data = json.loads(body)
                call_id = data.get('call_id', 'unknown')
                
                if call_id not in processed_calls:
                    processed_calls.add(call_id)
                    print(f"\n📞 FATHOM: {data.get('title', 'Unknown')} ({call_id})")
                    print(f"   Date: {data.get('date', 'N/A')[:10]} | Duration: {data.get('duration_seconds', 0)//60} min")
                    print(f"   → Slack #{SLACK_CHANNEL_ID}\n")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "received"}')
            except Exception as e:
                print(f"ERROR: {e}")
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

print(f"\n🚀 Fathom webhook running on port {PORT}")
print(f"   Health: /health")
print(f"   Webhook: /webhook/fathom\n")

server = HTTPServer(('0.0.0.0', PORT), Handler)
server.serve_forever()
