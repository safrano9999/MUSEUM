import http.server
import subprocess
import urllib.parse

class BridgeHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        
        if 'cmd' in params:
            command = params['cmd'][0]
            print(f"Führe aus: {command}")
            subprocess.Popen(command, shell=True)
            
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

if __name__ == "__main__":
    print("Brücke aktiv auf Port 8080...")
    http.server.HTTPServer(('localhost', 8080), BridgeHandler).serve_forever()
