from pycdplayer_server import server

server = server.Server()

try:
    server.run()
except KeyboardInterrupt:
    print("stopping")
    server.stop()
