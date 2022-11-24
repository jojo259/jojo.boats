# https://kendhia.medium.com/run-python-webserver-flask-as-a-websocket-client-also-175c130f7ca4

import pandasocket

def startFlask():
	import app # runs itself on import (too lazy to organize)
	# if flask is in debug mode then it errors with
	# OSError: [WinError 10038] An operation was attempted on something that is not a socket
	# production mode works fine
	# no clue

def startSocket():
	pandasocket.init()

if __name__ == '__main__':

	print('init main')

	import multiprocessing

	runFlask = multiprocessing.Process(target = startFlask)
	runSocket = multiprocessing.Process(target = startSocket)

	runFlask.start()
	runSocket.start()

	runFlask.join()
	runSocket.join()