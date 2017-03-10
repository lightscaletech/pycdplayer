from libcdplayer import libcdplayer
from pycdplayer_server import server

player = libcdplayer.Player()
player.play()
server = server.Server(player)
server.run()
