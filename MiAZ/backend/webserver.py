import http.server
import socketserver
import threading
import os
import sys
import time
import socket
import random

from MiAZ.backend.log import MiAZLog

class MiAZHTTPServer:
    def __init__(self, ENV):
        self.ENV = ENV
        self.log = MiAZLog('MiAZ.WebServer')
        self.host = '127.0.0.1'
        self.port = random.randint(65000, 65535)
        self.directory = ENV['LPATH']['HTML']
        self.httpd = None

    def is_port_in_use(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)  # avoid hanging if something's wrong
            result = s.connect_ex((self.host, self.port))
            return result == 0  # 0 means port is open/used

    def get_directory(self):
        return self.directory

    def get_host(self):
        return self.host

    def get_port(self):
        return self.port

    def start(self):
        handler = http.server.SimpleHTTPRequestHandler
        os.chdir(self.directory)  # Serve from this directory

        if self.is_port_in_use():
            self.port = random.randint(65000, 65535)
            self.log.warning(f"Previous port was in use. Binding now to port {self.port}")
            self.start()

        try:
            self.httpd = socketserver.TCPServer((self.host, self.port), handler)
            self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
            self.thread.start()
            self.log.info(f"Serving at http://{self.host}:{self.port}/")
        except Exception as error:
            # When MiAZ is stopped abruptly and a plugin is using
            # the webserver, it is not possible to reconnect to the same
            # port again.
            # Possible solutions:
            # 1. Wait some seconds and restart the app
            # 2. Use a random port
            # Using both approachs for safeguarding connections
            self.log.error(error)
            self.log.warning("Sleeping 5 seconds")
            time.sleep(3)
            self.stop()
            python = sys.executable
            script = self.ENV['APP']['RUNTIME']['EXEC']
            self.log.info(f"Application restart: {python} {script} {sys.argv[1:]}")
            os.execv(python, [python, script] + sys.argv[1:])

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
