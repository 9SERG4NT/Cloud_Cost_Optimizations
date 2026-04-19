import urllib.request
import urllib.error
import json

req = urllib.request.Request(
    'https://openrouter.ai/api/v1/chat/completions',
    method='POST'
)
req.add_header('Authorization', 'Bearer ') # user key was likely provided or default
req.add_header('Content-Type', 'application/json')
data = json.dumps({'model': 'google/gemini-2.5-pro', 'messages': [{'role': 'user', 'content': 'hello'}]}).encode('utf-8')

try:
    response = urllib.request.urlopen(req, data=data)
    print(response.getcode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
