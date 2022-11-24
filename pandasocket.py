print('init pandasocket')
print(__name__)

import websocket
import threading
from time import sleep
import json

def on_message(ws, curMsg):
	try:

		itemJson = json.loads(curMsg)
		ownerUuid = itemJson.get('item', {}).get('owner', 'null')
		print(f'new mystic from {ownerUuid}')
		# todo

	except Exception as e:
		print(f'pandasocket message ingest errored {e} on item {curMsg}')

def on_open(ws):
	print('websocket connected')

def on_close(ws):
	print("### closed ###")

if __name__ == 'pandasocket':
	print('connecting to websocket')
	#websocket.enableTrace(True)
	ws = websocket.WebSocketApp("wss://pitpanda.rocks/api/newmystics", on_message = on_message, on_close = on_close, on_open = on_open)
	wst = threading.Thread(target=ws.run_forever)
	wst.start()