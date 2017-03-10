from http.server import HTTPServer, SimpleHTTPRequestHandler

class Server():
    class APIHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('content-type', 'application/json')
            self.wfile.write(b"My name is Sam!")


    def __init__(self, player):
        self.player = player

    def run(self):
        self.httpserv = HTTPServer(("", 9111), self.APIHandler)
        self.httpserv.serve_forever()
