
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
import sys

class MockOllamaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/tags":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "models": [
                    {"name": "llama3:latest"},
                    {"name": "llava:13b"},
                    {"name": "qwen2:7b"}
                ]
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server = HTTPServer(('localhost', 11434), MockOllamaHandler)
    print("Mock Ollama server running on port 11434")
    server.serve_forever()

if __name__ == '__main__':
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    # Keep main thread alive long enough for tests or until interrupted
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
