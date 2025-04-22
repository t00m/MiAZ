import http.server
import socketserver
import threading
import os

from MiAZ.backend.log import MiAZLog

class MiAZHTTPServer:
    def __init__(self, ENV):
        # ~ super().__init__(host='127.0.0.1', port=8000, directory=ENV['LPATH']['HTML'])
        self.log = MiAZLog('MiAZ.WebServer')
        self.host = '127.0.0.1'
        self.port = 8000
        self.directory = ENV['LPATH']['HTML']
        self.httpd = None

    def get_directory(self):
        return self.directory

    def get_host(self):
        return self.host

    def get_port(self):
        return self.port

    def start(self):
        handler = http.server.SimpleHTTPRequestHandler
        os.chdir(self.directory)  # Serve from this directory

        try:
            self.httpd = socketserver.TCPServer((self.host, self.port), handler)
            self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.thread.start()
            self.log.info(f"Serving at http://{self.host}:{self.port}/")
        except OSError:
            self.stop()
            self.start()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.thread.join()
            self.log.info("Webserver stopped")

# Example usage in your GTK app
# ~ if __name__ == "__main__":
    # ~ server = MiAZHTTPServer(directory="static")
    # ~ server.start()

    # ~ # Keep your GTK app running here...
    # ~ input("Press Enter to quit...\n")
    # ~ server.stop()
