def sendDiscord(toSend, hookUrl):
	def sendDiscordPart(partToSend):
		url = hookUrl
		data = {}
		data["username"] = "jojo.boats"
		data["content"] = partToSend
		requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout = 10)
	
	for i in range(int(len(toSend) / 2000) + 1):
		sendDiscordPart(toSend[i * 2000:i* 2000 + 2000])