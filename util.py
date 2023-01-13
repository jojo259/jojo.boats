import time
import math
import requests

import pymongo

import database
import config
import indexertasker

def prettyTimeStr(theTime):
	curTime = time.time()

	timeDiff = abs(theTime - curTime)

	timeWord = ''

	if timeDiff < 1:
		return 'right now'
	elif timeDiff < 60:
		timeWord = 'second'
	elif timeDiff < 3600:
		timeWord = 'minute'
		timeDiff /= 60
	elif timeDiff < 86400:
		timeWord = 'hour'
		timeDiff /= 3600
	elif timeDiff < 2678400:
		timeWord = 'day'
		timeDiff /= 86400
	elif timeDiff < 31536000:
		timeWord = 'month'
		timeDiff /= 2678400
	else:
		timeWord = 'year'
		timeDiff /= 31536000

	timeDiff = math.floor(timeDiff)

	if timeDiff > 1:
		timeWord += 's'

	if theTime > curTime:
		return f'in {timeDiff} {timeWord}'
	else:
		return f'{timeDiff} {timeWord} ago'

def uuidToInt(uuid):
	uuid = uuid.replace('-', '') # remove potential dashes
	uuid = uuid[:12] # limit chars to save space (chance of collision is still literally zero)
	uuid = int(uuid, 16)
	return uuid

def intToUuid(uuid):
	uuid = str(hex(uuid))[2:]
	return uuid

def getFullUuid(uuid):
	fullUuidDoc = database.playersCol.find_one({'_id': {'$regex': f'^{uuid}.*$'}})
	if fullUuidDoc == None:
		return None
	return fullUuidDoc['_id']

def findFriendsPath(uuidA, uuidB):

	friendRoutes = {}
	uuidsCheckQueue = [uuidToInt(uuidA)]
	checkedUuids = {}

	friendDocsBatched = []

	for atLoop in range(2048):

		if len(uuidsCheckQueue) == 0:
			return 'no more uuids to check'

		atUuid = uuidsCheckQueue.pop(0)

		checkedUuids[atUuid] = True

		uuidFriends = []

		docGot = database.friendsCol.find_one({'_id': atUuid})

		if docGot != None:

			print(f'checking {atLoop + 1} uuid {atUuid} getting from db')

			uuidFriends = list(map(lambda x: int(x), docGot.get('friends', [])))

		else:

			print(f'checking {atLoop + 1} uuid {atUuid} getting from api')

			fullUuid = getFullUuid(intToUuid(atUuid))

			if fullUuid == None:
				print(f'full uuid not found for {atUuid}')
				continue

			indexertasker.pauseUntil = time.time() + 5
			apiUrl = f'https://api.hypixel.net/friends?key={config.hypixelApiKey}&uuid={fullUuid}'
			apiGot = {'success': False}
			while apiGot.get('success', False) == False:
				apiGot = requests.get(apiUrl, timeout = 3).json()
				if apiGot.get('success', False) == False:
					time.sleep(1)

			for friendRecord in apiGot.get('records', []):

				uuidOne = uuidToInt(friendRecord.get('uuidSender'))
				uuidTwo = uuidToInt(friendRecord.get('uuidReceiver'))

				otherUuid = uuidOne if uuidOne != atUuid else uuidTwo

				uuidFriends.append(otherUuid)

		friendsDoc = {'_id': atUuid, 'friends': []}

		for friendUuid in uuidFriends:

			if friendUuid not in checkedUuids:
				uuidsCheckQueue.append(friendUuid)
			friendsDoc['friends'].append(friendUuid)

			if friendUuid not in friendRoutes:
				friendRoutes[friendUuid] = atUuid

		if docGot == None:
			database.friendsCol.replace_one({'_id': atUuid}, friendsDoc, upsert = True)

		if uuidToInt(uuidB[:12]) in uuidFriends:
			break

	friendPath = [uuidToInt(uuidB)]

	for i in range(8):
		if friendPath[-1] != uuidToInt(uuidA):
			friendPath.append(friendRoutes[friendPath[-1]])

	friendPath = list(reversed(friendPath))

	friendPath = list(map(lambda x: intToUuid(x), friendPath))
	friendPath = list(map(lambda x: getFullUuid(x), friendPath))

	return friendPath