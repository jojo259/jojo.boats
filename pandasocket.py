import websocket
import _thread
import time
import rel
import json

def on_message(ws, curMsg):
	try:
		
		itemJson = json.loads(curMsg)
		ownerUuid = itemJson.get('item', {}).get('owner', 'null')
		print(f'new mystic from {ownerUuid}')
		# todo

	except Exception as e:
		print(f'pandasocket message ingest errored {e} on item {curMsg}')

# mostly copied

def on_error(ws, error):
	print(error)

def on_close(ws, close_status_code, close_msg):
	print("### closed ###")

def on_open(ws):
	print("Opened connection")

def init():
	#websocket.enableTrace(True)
	print('creating websocket')
	ws = websocket.WebSocketApp("wss://pitpanda.rocks/api/newmystics",
		on_open = on_open,
		on_message = on_message,
		on_error = on_error,
		on_close = on_close
	)

	ws.run_forever(dispatcher=rel, reconnect=5)  # Set dispatcher to automatic reconnection, 5 second reconnect delay if connection closed unexpectedly
	rel.signal(2, rel.abort)  # Keyboard Interrupt
	rel.dispatch()