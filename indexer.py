""""
	i have not read this code in like a year now
	do not judge it...
	hopefully it does not expose anything and is not incredibly buggy
"""

import requests
import time
import nbt
import io
import math
import random
from nbt.nbt import NBTFile, TAG_Long, TAG_Int, TAG_String, TAG_List, TAG_Compound

import config
import database

print('connecting')

import time

def genIndexTypes():
	curTime = time.time()

	indexTypes = {}
	#indexTypes['checkAll'] = {'persist.checkalltag': {'$exists': False}}
	#indexTypes['boatsWorkaround'] = {'$and': [{'nodata': {'$exists': False}}, {'persist.checkedpit': False}]}
	#indexTypes['noChecked'] = {'$and': [{'nodata': {'$exists': False}}, {'checktime': {'$exists': False}}]}
	indexTypes['tooOld'] = {'checktime':{'$lt': curTime - 86400 * 365}}

	indexTypes['onlineYear'] = {'$and':[{'lastsave':{'$gt': curTime - 86400 * 365}}, {'checktime':{'$lt': curTime - 86400 * 30}}]}
	indexTypes['onlineMonth'] = {'$and':[{'lastsave':{'$gt': curTime - 86400 * 30}}, {'checktime':{'$lt': curTime - 86400 * 7}}]}
	indexTypes['onlineWeek'] = {'$and':[{'lastsave':{'$gt': curTime - 86400 * 7}}, {'checktime':{'$lt': curTime - 86400 * 1}}]}
	#indexTypes['onlineDay'] = {'$and':[{'lastsave':{'$gt': curTime - 3600 * 24}}, {'checktime':{'$lt': curTime - 3600 * 1}}]}
	#indexTypes['onlineHour'] = {'$and':[{'lastsave':{'$gt': curTime - 60 * 60}}, {'checktime':{'$lt': curTime - 60 * 1}}]}

	indexTypes['checkNew'] = {'$or': [{'persist.checkedpit': False}, {'persist.checkedpit': {'$exists': False}}]}

	return indexTypes

def getHypixelApi(urlToGet):
	try:
		try:
			apiCalled = requests.get(urlToGet, timeout = 3)
			apiCalledJson = apiCalled.json()
			return apiCalledJson
		except Exception as e:
			print('api error, probably timeout, retrying')
			print(e)
			print(urlToGet)
	except Exception as e:
		print(e)
		print('error getHypixelApi')

def replaceColors(repStr):
	try:
		lastBad = False
		newStr = ''
		for i in range(len(repStr)):
			if not lastBad:
				curChar = repStr[i]
				if curChar == '§':
					lastBad = True
				elif curChar.isalnum():
					newStr += curChar
			else:
				lastBad = False
		return newStr
	except Exception as e:
		print(e)
		return ''

def addNewFriends():
	def findNewFriendUuid():
		newFriendToCheckDoc = database.playersCol.find_one({'$or':[{'persist.checkedfriends': {'$exists': False}}, {'persist.checkedfriends': False}]})
		if newFriendToCheckDoc != None:
			newFriendToCheckDocUuid = newFriendToCheckDoc['_id']
			return newFriendToCheckDoc['_id']
		print('couldnt find new friend to check uuid, doing jojo')
		return '1f2e58ced9164d55bd3fa7f4a81dd09f'

	def addFriends(checkUuid):
		if len(checkUuid) == 32:
			apiUrl = f'https://api.hypixel.net/friends?key={config.hypixelApiKey}&uuid={checkUuid}'
		else:
			apiUrl = f'https://api.hypixel.net/friends?key={config.hypixelApiKey}&name={checkUuid}'
		apiGot = getHypixelApi(apiUrl)

		newUuidsAdded = 0

		for curRecord in apiGot['records']:
			uuidSender = curRecord['uuidSender']
			uuidReceiver = curRecord['uuidReceiver']

			differentUuid = ''
			if uuidSender != checkUuid:
				differentUuid = uuidSender
			else:
				differentUuid = uuidReceiver

			addedFriend = addFlagToUuid(differentUuid, 'fromfriends', True)
			if addedFriend:
				newUuidsAdded += 1

		print(f'added friends from {checkUuid}: {newUuidsAdded}')

		addFlagToUuid(checkUuid, 'checkedfriends', True)

	checkUuid = findNewFriendUuid()

	addFriends(checkUuid)

def addPandaLeaderboardPage():
	try:
		global curPandaLeaderboardPage

		curPandaLeaderboardPage -= 1
		if curPandaLeaderboardPage < 0:
			curPandaLeaderboardPage = 4000

		apiUrl = f"https://pitpanda.rocks/api/leaderboard/xp?page={curPandaLeaderboardPage}"

		print(f"checking panda leaderboard page {curPandaLeaderboardPage}")

		apiGot = getHypixelApi(apiUrl)

		for curPlayer in apiGot['leaderboard']:
			playerUuid = curPlayer['uuid']
			addedNew = addFlagToUuid(playerUuid, 'frompanda', True)
			if addedNew:
				print(f'NEW panda {playerUuid}')
	except Exception as e:
		print(e)
		print('error addPandaLeaderboardPage')

def indexPlayer(givenUuid):
	#playerUuid = 'omicba'
	try:
		if '-' in givenUuid:
			print('	banned char, deleting uuid from database.playersCol')
			database.playersCol.delete_one({'_id': givenUuid})
			return

		playerUuid = givenUuid.replace('-', '')
		
		loopTimer = time.time()

		toUpsert = {}

		def addToUpsert(addVal, addKey):
			if addVal != None:
				toUpsert[addKey] = addVal

		if len(playerUuid) == 32:
			if playerUuid[12] != '4':
				print('	fake/malformed uuid, deleting')
				database.playersCol.delete_one({'_id': playerUuid})

				return

			apiUrl = f'https://api.hypixel.net/player?key={config.hypixelApiKey}&uuid={playerUuid}'
		else:
			apiUrl = f'https://api.hypixel.net/player?key={config.hypixelApiKey}&name={playerUuid}'

		apiTimer = time.time()

		apiGot = getHypixelApi(apiUrl)

		if 'success' in apiGot:
			if apiGot['success'] == True:
				#print(f'gotApi {int((time.time() - apiTimer) * 1000)}ms')

				addFlagToUuid(playerUuid, 'checkalltag', True)

				playerData = getVal(apiGot, ['player'])
				if playerData == None:
					addFlagToUuid(playerUuid, 'checkedpit', True)

					database.playersCol.delete_one({'_id': givenUuid})

					print('	null player')
					return

				playerUsername = getVal(apiGot, ['player', 'displayname'])
				playerUuidFromApi = getVal(apiGot, ['player', 'uuid'])

				if len(playerUuid) != 32:
					database.playersCol.delete_one({'_id': givenUuid})
					print('	deleted original username doc, using uuid from api')
					playerUuid = playerUuidFromApi.replace('-', '')

				playerRank = getVal(apiGot, ['player', 'rank'])
				if playerRank == None:
					playerRank = getVal(apiGot, ['player', 'newPackageRank'])
					if playerRank == None:
						playerRank = getVal(apiGot, ['player', 'packageRank'])
						if playerRank == None:
							playerRank = getVal(apiGot, ['player', 'monthlyPackageRank'])
				if playerRank == 'NORMAL' or playerRank == 'VIP' or playerRank == 'VIP_PLUS' or playerRank == 'MVP' or playerRank == 'MVP_PLUS':
					playerRank = None # don't wanna store it unless interesting

				playerPrefix = getVal(apiGot, ['player', 'prefix'])

				#print(playerRank)

				#playerFirstLogin = getVal(apiGot, ['player', 'firstLogin'])
				#playerRankPlusColor = getVal(apiGot, ['player', 'rankPlusColor'])

				curTime = int(time.time())

				addToUpsert(playerUsername, 'username')
				#addToUpsert(playerUuid.replace('-',''), '_id')
				addToUpsert(curTime, 'checktime')
				addToUpsert(playerRank, 'rank')
				#addToUpsert(playerFirstLogin, 'firstlogin')
				#addToUpsert(playerRankPlusColor, 'rankpluscolor')
				addToUpsert(playerPrefix, 'prefix')

				lastSave = getVal(apiGot, ['player', 'stats', 'Pit', 'profile', 'last_save'])

				if lastSave != None:
					lastSave = int(lastSave / 1000)

				addToUpsert(lastSave, 'lastsave')

				#playerXp = getVal(apiGot, ['player', 'stats', 'Pit', 'profile', 'xp'])

				#addToUpsert(playerXp, 'xp')

				#print(f'	deletingMany')

				deletedItems = database.itemsCol.delete_many({'owner': playerUuid})

				print(f'	deletedMany {int((time.time() - loopTimer) * 1000)}ms')

				'''
				ORDER MUST BE: (?? probably)
				- delete items
				- get player stats, if no stats then return
				- upsert player
				- iterate items
				'''

				# check if from panda
				playerFromPanda = False
				playerDoc = database.playersCol.find_one({'_id': playerUuidFromApi})
				if playerDoc != None:
					if getVal(playerDoc, ['persist', 'frompanda']) == True:
						playerFromPanda = True

				#print(f'insertedItems {int((time.time() - loopTimer) * 1000)}ms')
				
				#print(f'	finding uuids')
				uuidsFound = findUuids(apiGot)
				print(f'	foundUuids {int((time.time() - loopTimer) * 1000)}ms')

				playerPitStats = getVal(apiGot, ['player', 'stats', 'Pit'])
				if playerPitStats == None:
					playerDocAlready = database.playersCol.find_one({'_id': playerUuid})
					if playerDocAlready != None:
						if 'persist' in playerDocAlready:
							toUpsert['persist'] = playerDocAlready['persist']

					database.playersCol.replace_one({'_id': playerUuid}, toUpsert, upsert = True)

					addFlagToUuid(playerUuid, 'checkedpit', True)
					addFlagToUuid(playerUuid, 'haspit', False)
					# database.playersCol.delete_one({'_id': playerUuid}) no more since merge
					print('	no pit data')
					return
				addFlagToUuid(playerUuid, 'haspit', True) # ??

				itemsToInsert = []
				playerItems = getItems(apiGot)
				for curItem in playerItems:
					#print('item')
					itemName = getVal(curItem, ['tag','display','Name'])
					itemNameClean = None
					if itemName != None:
						itemNameClean = replaceColors(itemName).lower()
					itemCount = getVal(curItem, ['Count'])
					if itemCount == None: itemCount = 1
					itemVanillaEnchants = getVal(curItem, ['tag', 'ench'])
					itemPitEnchants = getVal(curItem, ['tag','ExtraAttributes','CustomEnchants'])
					itemNonce = getVal(curItem, ['tag','ExtraAttributes','Nonce'])
					itemLives = getVal(curItem, ['tag','ExtraAttributes','Lives'])
					itemMaxLives = getVal(curItem, ['tag','ExtraAttributes','MaxLives'])
					itemTier = getVal(curItem, ['tag','ExtraAttributes','UpgradeTier'])
					itemGemmed = getVal(curItem, ['tag','ExtraAttributes','UpgradeGemsUses'])
					itemGemmed = True if itemGemmed == 1 else None
					itemId = getVal(curItem, ['id'])
					itemColor = getVal(curItem, ['tag','display','color'])
					itemLore = getVal(curItem, ['tag','display','Lore'])

					if itemId == 262 and itemName == None and itemLore == None:
						continue # skip item if plain arrow

					itemTokens = 0
					if itemPitEnchants != None:
						addToUpsert(True, 'hasmystics')

						for curEnchant in itemPitEnchants:
							itemTokens += curEnchant['Level']

					if itemTokens == 0:
						itemTokens = None


					toInsert = {}

					def addItemVal(addKey, addVal):
						if addVal != None and addVal != []:
							toInsert[addKey] = addVal

					addItemVal('name', itemName)
					addItemVal('nameclean', itemNameClean)
					addItemVal('count', itemCount)
					addItemVal('enchvanilla', itemVanillaEnchants)
					addItemVal('enchpit', itemPitEnchants)
					addItemVal('nonce', itemNonce)
					addItemVal('lives', itemLives)
					addItemVal('maxlives', itemMaxLives)
					addItemVal('tier', itemTier)
					addItemVal('gemmed', itemGemmed)
					addItemVal('id', itemId)
					addItemVal('color', itemColor)
					addItemVal('lore', itemLore)
					addItemVal('owner', playerUuid)
					addItemVal('ownerusername', playerUsername)
					addItemVal('lastsave', lastSave)
					addItemVal('tokens', itemTokens)
					if playerFromPanda:
						addItemVal('frompanda', True)

					#print(curItem)

					itemsToInsert.append(toInsert)
					#print(f'inserted {itemName if itemName != None else itemId}')
					#print('done item')

				print(f'	readItems {int((time.time() - loopTimer) * 1000)}ms')

				playerDocAlready = database.playersCol.find_one({'_id': playerUuid})
				if playerDocAlready != None:
					if 'persist' in playerDocAlready:
						toUpsert['persist'] = playerDocAlready['persist']
						toUpsert['persist']['checkedpit'] = True

				database.playersCol.replace_one({'_id': playerUuid}, toUpsert, upsert = True)
				addFlagToUuid(playerUuid, 'checkedpit', True) # REORGANIZE ? idk

				if len(itemsToInsert) > 0:
					#print('inserting')
					database.itemsCol.insert_many(itemsToInsert)
					#print('done')

				print(f'	insertedItems {int((time.time() - loopTimer) * 1000)}ms')

				#print(f'addedFlag {int((time.time() - loopTimer) * 1000)}ms')
			elif apiGot['success'] == False:
				print('	success false')
				if apiGot['cause'] == 'Malformed UUID':
					print('	malformed UUID, deleting')
					database.playersCol.delete_one({'_id': playerUuid})
				elif apiGot['cause'] == 'You have already looked up this name recently':
					print('	looked up too recently')
				else:
					print('	' + str(apiGot)[:64].replace('\n', ''))

	except Exception as e:
		print(e)
		print('error indexPlayer')

def findUuids(apiData):
	#print('finding uuids')
	uuidsList = []

	possibleRoutes = [['player', 'friendBlocksUuid'], ['player', 'friendRequests'], ['player', 'friendRequestsUuid'], ['player', 'mostRecentlyThankedUuid'], ['player', 'mostRecentlyTippedUuid'], ['player', 'stats', 'SkyWars', 'head_collection', 'recent'], ['player', 'stats', 'SkyWars', 'head_collection', 'prestigious']]

	def possibleUuid(checkUuid):
		if len(checkUuid) == 32:
			if checkUuid[12] == '4':
				uuidsList.append(checkUuid)
				addFlagToUuid(checkUuid, 'fromplayer', True)

	for possibleRoute in possibleRoutes:
		routeVal = getVal(apiData, possibleRoute)
		if isinstance(routeVal, str):
			possibleUuid(routeVal)
		elif isinstance(routeVal, list):
			for curItem in routeVal:
				if isinstance(curItem, str):
					possibleUuid(curItem)
				if 'uuid' in curItem:
					possibleUuid(curItem['uuid'])
		elif isinstance(routeVal, dict):
			for dictKey, dictVal in routeVal:
				if 'uuid' in dictKey.lower():
					possibleUuid(dictVal)

	return uuidsList

def addFlagToUuid(uuidTo, flagTo, flagVal):
	try:
		database.playersCol.insert_one({'_id': uuidTo, 'persist': {flagTo: flagVal}})
		return True
	except:
		playerDoc = database.playersCol.find_one({'_id': uuidTo})
		if 'persist' in playerDoc:
			playerDoc['persist'][flagTo] = flagVal
		else:
			playerDoc['persist'] = {}
			playerDoc['persist'][flagTo] = flagVal
		database.playersCol.replace_one({'_id': uuidTo}, playerDoc)
		if flagTo == 'frompanda':
			database.itemsCol.update_many({'owner':uuidTo}, {'$set':{'frompanda': True}})
		return False

def getVal(theDict, thePath):
	try:
		try:
			for i in range(len(thePath)):
				theDict = theDict[thePath[0]]
				thePath.pop(0)
			return theDict
		except:
			return None
	except:
		print('error getVal')

def getItems(playerData):
	try:
		def unpack_nbt(tag): #credit CrypticPlasma on hypixel forums
			"""
			Unpack an NBT tag into a native Python data structure.
			"""

			if isinstance(tag, TAG_List):
				return [unpack_nbt(i) for i in tag.tags]
			elif isinstance(tag, TAG_Compound):
				return dict((i.name, unpack_nbt(i)) for i in tag.tags)
			else:
				return tag.value

		def decode_nbt(raw): #credit CrypticPlasma on hypixel forums, modified
			"""
			Decode a gziped and base64 decoded string to an NBT object
			"""

			return nbt.nbt.NBTFile(fileobj=io.BytesIO(raw))

		items = []
		toDecode = []

		toDecode.append(getVal(playerData, ['player','stats','Pit','profile','inv_contents','data'])) #inventory
		toDecode.append(getVal(playerData, ['player','stats','Pit','profile','inv_enderchest','data'])) #enderchest
		toDecode.append(getVal(playerData, ['player','stats','Pit','profile','item_stash','data'])) #stash
		toDecode.append(getVal(playerData, ['player','stats','Pit','profile','spire_stash_inv','data'])) #spire stash
		toDecode.append(getVal(playerData, ['player','stats','Pit','profile','inv_armor','data'])) #armor
		toDecode.append(getVal(playerData, ['player','stats','Pit','profile','mystic_well_item','data'])) #mystic well item
		toDecode.append(getVal(playerData, ['player','stats','Pit','profile','mystic_well_pants','data'])) #mystic well pants
		
		for curDecode in toDecode:
			if curDecode != None:
				temp = []
				for x in curDecode:
					if x < 0:
						temp.append(x + 256)
					else:
						temp.append(x)
				decoded = decode_nbt(bytes(temp))
				for tagl in decoded.tags:
					for tagd in tagl.tags:
						try:
							unpacked = unpack_nbt(tagd)
							if unpacked != {}:
								items.append(unpacked)
						except Exception as e:
							print(e)
							pass

		return items
	except Exception as e:
		print(e)
		print('error getItems')
		return []

print('starting')

indexedTimes = []

curPandaLeaderboardPage = 4000
lastQuery = None

def doLoop():
	global indexedTimes

	try:
		loopTimer = time.time()

		curTime = time.time()

		if random.randint(1, 256) == 1:
			addPandaLeaderboardPage()

			return

		indexTypes = genIndexTypes()

		doneIndex = False

		for indexName, indexQuery in indexTypes.items():
			if indexName == 'randomOld':
				if random.randint(1, 32) != 1:
					continue

			print(f'	checking {indexName}')
			foundDoc = database.playersCol.find_one(indexQuery)
			if foundDoc != None:
				print(f'	foundDoc {int((time.time() - loopTimer) * 1000)}ms')
				docUuid = foundDoc['_id']

				print(f'indexing {docUuid} {indexName} indexedTimes = {int(len(indexedTimes))}')
				indexPlayer(docUuid)

				print(f'	finishedIndex {int((time.time() - loopTimer) * 1000)}ms')

				doneIndex = True

				break
			print(f'	checked {indexName} {int((time.time() - loopTimer) * 1000)}ms')

		if not doneIndex:
			for i in range(128):
				addNewFriends()

		if True:
			indexedTimes.append(curTime)
			indexedTimes = list(filter(lambda x: x > curTime - 60, indexedTimes))

		print(f'	loopTimer {int((time.time() - loopTimer) * 1000)}ms')
	except Exception as e:
		print(e)
		print('error mainloop')