from libcdplayer import libcdplayer
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler

import json

player = libcdplayer.Player()

class APIHandler(SimpleHTTPRequestHandler):

    CODE_SUCCESS   = HTTPStatus.OK
    CODE_NOT_FOUND = HTTPStatus.NOT_FOUND
    CODE_ERROR     = HTTPStatus.INTERNAL_SERVER_ERROR

    def resp(self, c, d = {}): return (c, bytes(json.dumps(d), 'utf-8'))
    def success(self, d):      return self.resp(self.CODE_SUCCESS, d)
    def error(self, d):        return self.resp(self.CODE_ERROR, d)
    def not_found(self):       return self.resp(self.CODE_NOT_FOUND)

    def track(self, segs):
        if segs[0] == 'set':
            num = int(segs[1])
            player.set_track(num)
            return self.success({'status': 'success'})

        return self.not_found()

    def pause(self):
        player.pause()
        return self.success({'status': 'success'})

    def play(self):
        player.play()
        return self.success({'status': 'success'})

    def route(self, segs):
        if   segs[0] == 'track': return self.track(segs[1:])
        elif segs[0] == 'pause': return self.pause()
        elif segs[0] == 'play':  return self.play()

        return self.not_found()

    def do_GET(self):
        path = self.path
        segs = []
        for s in path.split('/'):
            if len(s) > 0: segs.append(s)

        code, data = self.route(segs)
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        self.end_headers()
        self.wfile.write(data)

class Server():
    def __init__(self): pass

    def run(self):
        player.play()
        self.httpserv = HTTPServer(("", 9111), APIHandler)
        self.httpserv.serve_forever()

    def stop(self):
        player.stop()
