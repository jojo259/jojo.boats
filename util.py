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