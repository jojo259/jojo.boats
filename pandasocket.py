print('init pandasocket')

import websocket
import threading
from time import sleep
import json
import rel

import indexertasker

def on_message(ws, curMsg):
	try:

		itemJson = json.loads(curMsg)
		ownerUuid = itemJson.get('item', {}).get('owner', 'null')
		print(f'new mystic from {ownerUuid}')

		indexertasker.addToIndexerQueue(ownerUuid)

	except Exception as e:
		print(f'pandasocket message ingest errored {e} on item {curMsg}')

def on_open(ws):
	print('websocket connected')

def on_close(ws):
	print("websocket closed")

def on_error(ws, error):
	print(error)

if __name__ == 'pandasocket':
	print('connecting to websocket')
	#websocket.enableTrace(True)
	ws = websocket.WebSocketApp("wss://pitpanda.rocks/api/newmystics", on_message = on_message, on_close = on_close, on_open = on_open, on_error = on_error)
	wst = threading.Thread(target=ws.run_forever, kwargs={'reconnect': 5})
	wst.start()