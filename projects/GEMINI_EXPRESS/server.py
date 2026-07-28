import http.server
import os

# Verzeichnis, in dem das Skript liegt
LOG_DIR = os.path.dirname(os.path.abspath(__file__))

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=LOG_DIR, **kwargs)

if __name__ == "__main__":
    print(f"Datei-Server aktiv auf Port 8000 (Pfad: {LOG_DIR})")
    http.server.HTTPServer(('localhost', 8000), MyHandler).serve_forever()
