import requests

def sendDiscord(toSend, hookUrl):
	def sendDiscordPart(partToSend):
		url = hookUrl
		data = {}
		data["username"] = "jojo.boats"
		data["content"] = partToSend
		requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout = 10)

	toSend = str(toSend)
	toSend = toSend.replace('@', 'at')
	
	for i in range(int(len(toSend) / 1998) + 1):
		sendDiscordPart('`' + toSend[i * 1998:i* 1998 + 1998] + '`')