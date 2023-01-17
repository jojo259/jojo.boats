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

def addFlagToUuid(uuidTo, flagTo, flagVal):
	try:
		database.playersCol.insert_one({'_id': uuidTo, 'persist': {flagTo: flagVal}})
		return True
	except:
		playerDoc = database.playersCol.find_one({'_id': uuidTo})
		if 'persist' in playerDoc:
			playerDoc['persist'][flagTo] = flagVal
		else:
			playerDoc['persist'] = {flagTo: flagVal}
		database.playersCol.replace_one({'_id': uuidTo}, playerDoc)
		if flagTo == 'frompanda':
			database.itemsCol.update_many({'owner':uuidTo}, {'$set':{'frompanda': True}})
			database.mysticsCol.update_many({'item.owner':uuidTo}, {'$set':{'item.frompanda': True}})
		return False

def uuidToInt(uuid):
	uuid = uuid.replace('-', '') # remove potential dashes
	uuid = uuid[:12] # limit chars to save space (chance of collision is still literally zero)
	uuid = int(uuid, 16)
	return uuid

def intToShortenedUuid(uuid):
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

	fetchedFriendsLists = {}
	friendsListsSinceFetched = 248 # will try to start fetching after 8 initial friends lists

	for atLoop in range(4096):

		if len(uuidsCheckQueue) == 0:
			return None

		atUuid = uuidsCheckQueue.pop(0)

		checkedUuids[atUuid] = True

		if friendsListsSinceFetched > 256:
			friendsListsSinceFetched = 0
			fetchedFriendsDocsList = database.friendsCol.find({'_id': {'$in': uuidsCheckQueue[:256]}})
			fetchedFriendsLists = {}
			for friendsDoc in fetchedFriendsDocsList:
				fetchedFriendsLists[friendsDoc['_id']] = friendsDoc['friends']
			print(f'fetched {len(fetchedFriendsLists.keys())} friends lists from db')

		friendsListsSinceFetched += 1

		uuidFriends = fetchedFriendsLists.get(atUuid)
		if uuidFriends == None:
			fullUuid = getFullUuid(intToShortenedUuid(atUuid))

			if fullUuid == None:
				print(f'full uuid not found for {atUuid}')
				continue

			print(f'getting friends for {fullUuid}')
			uuidFriends = getFriendsFor(fullUuid, intifyFriends = True)
		else:
			print(f'got friends list from fetched for {atUuid}')

		if uuidFriends == None:
			continue

		for friendUuid in uuidFriends:

			if friendUuid not in checkedUuids:
				uuidsCheckQueue.append(friendUuid)

			if friendUuid not in friendRoutes:
				friendRoutes[friendUuid] = atUuid

		if uuidToInt(uuidB) in uuidFriends:
			break

	friendPath = [uuidToInt(uuidB)]

	for i in range(8):
		if friendPath[-1] != uuidToInt(uuidA):
			friendPath.append(friendRoutes.get(friendPath[-1], 0))

	friendPath = list(reversed(friendPath))

	friendPath = list(map(lambda x: getFullUuid(intToShortenedUuid(x)), friendPath))

	return friendPath

def getFriendsFor(playerUuid, intifyFriends = False):

	uuidInt = uuidToInt(playerUuid)

	docGot = database.friendsCol.find_one({'_id': uuidInt})

	if docGot != None:
		playerFriendsInts = docGot['friends']
		if intifyFriends:
			return playerFriendsInts
		else:
			return list(map(lambda x: getFullUuid(intToShortenedUuid(x)), playerFriendsInts))

	while indexertasker.apiQueriesThisMinute >= 120:
		time.sleep(1)

	indexertasker.apiQueriesThisMinute += 1

	apiUrl = f'https://api.hypixel.net/friends?key={config.hypixelApiKey}&uuid={playerUuid}'
	try:
		apiGot = requests.get(apiUrl, timeout = 3).json()
	except Exception as e:
		print(f'getFriendsFor error: {e}')
		return None

	playerFriends = []
	batchedOtherFriendDocAdds = []

	for friendRecord in apiGot.get('records', []):

		uuidOne = friendRecord['uuidSender']
		uuidTwo = friendRecord['uuidReceiver']

		otherUuid = uuidOne if uuidOne != playerUuid else uuidTwo

		playerFriends.append(otherUuid)

		batchedOtherFriendDocAdds.append(pymongo.UpdateOne({'_id': uuidToInt(otherUuid)}, {'$addToSet': {'friends': uuidInt}}, upsert = True))

	# add to database

	if len(batchedOtherFriendDocAdds) > 0:
		database.friendsCol.bulk_write(batchedOtherFriendDocAdds)

	playerFriendsInts = list(map(lambda x: uuidToInt(x), playerFriends))

	friendsDoc = {'_id': uuidInt, 'friends': playerFriendsInts}
	database.friendsCol.replace_one({'_id': uuidInt}, friendsDoc, upsert = True)

	addFlagToUuid(playerUuid, 'checkedfriends', True)

	# return results

	if intifyFriends:
		return playerFriendsInts
	else:
		return playerFriends