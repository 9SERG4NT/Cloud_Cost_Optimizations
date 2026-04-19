import os
import urllib.request
import urllib.error
import json

req = urllib.request.Request(
    'https://api.groq.com/openai/v1/chat/completions',
    method='POST'
)
req.add_header('Authorization', f"Bearer {os.getenv('GROQ_API_KEY')}")
req.add_header('Content-Type', 'application/json')
data = json.dumps({'model': 'llama-3.1-8b-instant', 'messages': [{'role': 'user', 'content': 'hello'}]}).encode('utf-8')

try:
    response = urllib.request.urlopen(req, data=data)
    print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode())
