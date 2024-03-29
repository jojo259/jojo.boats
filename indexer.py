""""
	i have not read this code in like a year now
	do not judge it...
	hopefully it does not expose anything and is not incredibly buggy
"""

import requests
import time
import io
import math
import random
import copy

import nbt
from nbt.nbt import NBTFile, TAG_Long, TAG_Int, TAG_String, TAG_List, TAG_Compound
import pymongo
import bson

import config
import database
import discordsender
import indexerstats
import util
import indexertasker

print('connecting')

def genIndexTypes():
	curTime = time.time()

	indexTypes = {}

	indexTypes['missingCheckAt'] = {'$and': [{'checkat': {'$exists': False}}, {'hasmystics': True}]}
	indexTypes['checkAt'] = {'checkat': {'$lt': curTime}}

	indexTypes['checkNew'] = {'$or': [{'persist.checkedpit': False}, {'persist.checkedpit': {'$exists': False}}]}

	return indexTypes

def getHypixelApi(urlToGet):
	for i in range(64):
		try:
			apiGot = requests.get(urlToGet, timeout = 10).json()
			if apiGot.get('success') == True:
				return apiGot
		except Exception as e:
			print(f'getHypixelApi{urlToGet} {e}')
		time.sleep(1)
	print(f'getHypixelApi {urlToGet} error')
	return {'success': False}

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

def addPandaLeaderboardPage():
	global curPandaLeaderboardPage

	curPandaLeaderboardPage -= 1
	if curPandaLeaderboardPage < 0:
		curPandaLeaderboardPage = 4000

	apiUrl = f"https://pitpanda.rocks/api/leaderboard/xp?page={curPandaLeaderboardPage}"

	print(f"checking panda leaderboard page {curPandaLeaderboardPage}")

	apiGot = getHypixelApi(apiUrl)

	for curPlayer in apiGot.get('leaderboard', []):
		playerUuid = curPlayer.get('uuid', '')
		addedNew = util.addFlagToUuid(playerUuid, 'frompanda', True)
		if addedNew:
			print(f'NEW panda {playerUuid}')

def addNewGuildMembers(playerUuid):

	apiUrl = f'https://api.hypixel.net/guild?key={config.hypixelApiKey}&player={playerUuid}'
	apiGot = getHypixelApi(apiUrl)

	playerGuild = apiGot.get('guild', {})
	if playerGuild == None:
		print('		player has no guild')
		return

	for memberData in playerGuild.get('members', []):
		memberUuid = memberData.get('uuid', '')
		print(f'		found guild member {memberUuid}')
		util.addFlagToUuid(memberUuid, 'fromguild', True)

	util.addFlagToUuid(playerUuid, 'checkedguild', True)

def indexPlayer(givenUuid):

	if givenUuid == None:
		print('	wtf null uuid, deleting') # seems to come from friends lists occasionally
		database.playersCol.delete_one({'_id': None})
		return

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

			util.addFlagToUuid(playerUuid, 'checkalltag', True)

			playerData = getVal(apiGot, ['player'])
			if playerData == None:
				util.addFlagToUuid(playerUuid, 'checkedpit', True)

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
			if lastSave == None:
				lastSave = 0

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

			# add player's guild members if not already checked

			if playerDoc != None:
				if playerDoc.get('persist', {}).get('checkedguild') != True and indexertasker.apiQueriesThisMinute < 120:
					addNewGuildMembers(playerUuid)

			#print(f'insertedItems {int((time.time() - loopTimer) * 1000)}ms')

			uuidsFound = findUuids(apiGot)
			print(f'	foundUuids {int((time.time() - loopTimer) * 1000)}ms')

			playerPitStats = getVal(apiGot, ['player', 'stats', 'Pit'])
			if playerPitStats == None:
				playerDocAlready = database.playersCol.find_one({'_id': playerUuid})
				if playerDocAlready != None:
					if 'persist' in playerDocAlready:
						toUpsert['persist'] = playerDocAlready['persist']

				database.playersCol.replace_one({'_id': playerUuid}, toUpsert, upsert = True)

				util.addFlagToUuid(playerUuid, 'checkedpit', True)
				util.addFlagToUuid(playerUuid, 'haspit', False)
				addToUpsert(curTime + 86400 * 365, 'checkat')
				print('	no pit data')
				return
			util.addFlagToUuid(playerUuid, 'haspit', True) # ??

			mysticsColOperations = []
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
				itemGemmed = True if itemGemmed == 1 else False
				itemId = getVal(curItem, ['id'])
				itemColor = getVal(curItem, ['tag','display','color'])
				itemLore = getVal(curItem, ['tag','display','Lore'])

				if (itemId == 49 or itemId == 262) and itemName == None and itemLore == None:
					continue # skip item if plain arrow

				itemTokens = 0
				if itemPitEnchants != None:
					for curEnchant in itemPitEnchants:
						itemTokens += curEnchant['Level']

				toInsert = {}

				def addItemVal(addKey, addVal):
					if addVal != None and addVal != []:
						toInsert[addKey] = addVal

				# stupid setup
				addItemVal('name', itemName)
				addItemVal('nameclean', itemNameClean)
				addItemVal('count', itemCount)
				addItemVal('enchvanilla', itemVanillaEnchants)
				addItemVal('enchpit', itemPitEnchants)
				addItemVal('nonce', itemNonce)
				addItemVal('lives', itemLives)
				addItemVal('maxlives', itemMaxLives)
				addItemVal('tier', itemTier)
				addItemVal('id', itemId)
				addItemVal('color', itemColor)
				addItemVal('lore', itemLore)
				addItemVal('owner', playerUuid)
				addItemVal('ownerusername', playerUsername)
				addItemVal('lastsave', lastSave)
				if itemTokens != 0:
					addItemVal('tokens', itemTokens)
				if itemGemmed != False:
					addItemVal('gemmed', itemGemmed)
				if playerFromPanda:
					addItemVal('frompanda', True)

				#itemsToInsert.append(toInsert) # moved and duplicated bc this code is structured terribly...

				# mystic logging (.js haha funny pit panda source code reference)

				if itemNonce == None:
					itemsToInsert.append(toInsert)
					continue # no nonce, can't track
				if itemNonce >= 0 and itemNonce <= 16:
					itemsToInsert.append(toInsert)
					continue # not regular mystic, can't track

				duplicateNonceDocs = list(database.mysticsCol.find({'item.nonce': itemNonce})) # could batch all these into one if slow (should be fine)
				duplicateNonceCount = len(duplicateNonceDocs)

				# process item

				newObjectId = bson.ObjectId()
				newMysticDoc = {'_id': newObjectId, 'item': copy.deepcopy(toInsert), 'owners': [{'uuid': playerUuid, 'first': curTime, 'last': curTime}]} # without copy it was getting the ObjectID from when the item was inserted into the items col...

				if duplicateNonceCount == 0:

					# item has no duplicate nonce so it's a new item so insert

					print(f'		mystic has {len(duplicateNonceDocs)} duplicate nonces')

					mysticsColOperations.append(pymongo.InsertOne(newMysticDoc))

					toInsert.update({'mysticid': str(newObjectId)})
					itemsToInsert.append(toInsert)

					continue

				else:

					# item has duplicate nonce so check if item already in database or if it's new

					foundItemInDb = False

					for alrItemData in duplicateNonceDocs:

						alrItem = alrItemData.get('item', {})

						if alrItem.get('nonce', 0) != itemNonce:
							continue # sanity check...

						# check enchants to find the number of new tokens and do some simple checks

						tokensDiff = 0

						for curItemEnch in itemPitEnchants: # can also add check to see if an enchant was lost (which would mean they are different items)

							enchSeen = False
							curEnchLevel = curItemEnch.get('Level', -99)

							for alrItemEnch in alrItem.get('enchpit', []):

								if alrItemEnch.get('Key') == curItemEnch.get('Key'):

									# found same ench

									enchSeen = True
									alrEnchLevel = alrItemEnch.get('Level', 99)
									levelDiff = curEnchLevel - alrEnchLevel
									tokensDiff += levelDiff
									break

							if not enchSeen:
								tokensDiff += curEnchLevel

						# check tier difference

						tierDiff = itemTier - alrItem.get('tier', 99) # 99 to trigger if statement "tierDiff < 0"

						if tierDiff < 0:
							# tier went down which is impossible (besides jewels but whatever) so different item
							continue

						# check for known patterns and modify mystic doc appropriately

						seemsNewlyGemmed = itemGemmed and (alrItem.get('gemmed') == None or alrItem.get('gemmed') == False)

						if tierDiff == 0 and tokensDiff == 0:
							# same item no changes
							pass
						elif tierDiff == 1 and itemTier == 1 and tokensDiff <= 2 and tokensDiff >= 1 and itemTokens >= 1 and itemTokens <= 2:
							# tier 0 --> tier 1
							indexerstats.incStat('upgradedtotier1')
							alrItemData['tier1seenat'] = curTime
						elif tierDiff == 1 and itemTier == 2 and tokensDiff <= 2 and tokensDiff >= 1 and itemTokens >= 2 and itemTokens <= 4:
							# tier 1 --> tier 2
							indexerstats.incStat('upgradedtotier2')
							alrItemData['tier1'] = alrItem.get('enchpit', [])
							alrItemData['tier2seenat'] = curTime
						elif tierDiff == 1 and itemTier == 3 and (tokensDiff <= 4 or (tokensDiff <= 5 and itemGemmed and seemsNewlyGemmed)) and tokensDiff >= 1 and itemTokens >= 3 and itemTokens <= 8:
							# tier 2 --> tier 3 and potentially gemmed
							indexerstats.incStat('upgradedtotier3')
							alrItemData['tier2'] = alrItem.get('enchpit', [])
							alrItemData['tier3seenat'] = curTime
						elif tierDiff == 2 and itemTier == 2 and tokensDiff <= 4 and tokensDiff >= 2 and itemTokens >= 2 and itemTokens <= 4:
							# tier 0 --> tier 2
							indexerstats.incStat('upgradedtotier2')
							alrItemData['tier2seenat'] = curTime
						elif tierDiff == 2 and itemTier == 3 and (tokensDiff <= 6 or (tokensDiff <= 7 and itemGemmed and seemsNewlyGemmed)) and tokensDiff >= 2 and itemTokens >= 3 and itemTokens <= 8:
							# tier 1 --> tier 3 and potentially gemmed
							indexerstats.incStat('upgradedtotier3')
							alrItemData['tier1'] = alrItem.get('enchpit', [])
							alrItemData['tier3seenat'] = curTime
						elif tierDiff == 3 and itemTier == 3 and tokensDiff <= 8 and tokensDiff >= 3 and tokensDiff >= 2 and itemTokens >= 3 and itemTokens <= 8:
							# tier 0 --> tier 3
							indexerstats.incStat('upgradedtotier3')
							alrItemData['tier3seenat'] = curTime
						elif tierDiff == 0 and itemTier == 3 and tokensDiff == 1 and itemTokens >= 3 and itemTokens <= 8 and itemGemmed and seemsNewlyGemmed: # alrItem.get('gemmed') should be None but could be False in future
							# gemmed (can only gem at t3)
							pass
						else:
							# unknown pattern so not same item
							continue

						# this is (almost certainly) the same item

						if seemsNewlyGemmed:
							indexerstats.incStat('gemmed')
							alrItemData['gemseenat'] = curTime

						alrItemData['item'] = copy.deepcopy(toInsert)

						foundItemInDb = True

						itemDiffStr = f'itemTier {itemTier} tierDiff {tierDiff} tokensDiff {tokensDiff} itemNonce {itemNonce} itemOwner {playerUuid}'
						print(f'		found item ({len(duplicateNonceDocs)} duplicates) in db {itemDiffStr}')

						# do owner history

						if itemTier > 0: # don't do owner history for tier 0s because it will often be inaccurate due to duplicate nonce auction pants and duped items and who cares about fresh
							if alrItemData['owners'][-1]['uuid'] == playerUuid:

								# item owner is the same so just update the last seen time
								alrItemData['owners'][-1]['last'] = lastSave # update owner history to lastSave rather than curTime

							else:

								# item owner is not the same so append new entry to owners list
								print('			item has new owner')
								alrItemData['owners'].append({'uuid': playerUuid, 'first': lastSave, 'last': lastSave})
								indexerstats.incStat('ownerchanges')

						elif itemTier == 0:

							# update last seen time on owner history if still with same player

							if alrItemData['owners'][-1]['uuid'] == playerUuid:
								alrItemData['owners'][-1]['last'] = lastSave

						# add mystic doc to bulk operations lists

						toInsert.update({'mysticid': str(alrItemData['_id'])})
						itemsToInsert.append(toInsert)

						mysticsColOperations.append(pymongo.ReplaceOne({'_id': alrItemData['_id']}, alrItemData))
						
						break

					if not foundItemInDb:

						# didnt find item in db, new item

						print(f'		didnt find item in db')

						indexerstats.incStat('newregularmystic')

						toInsert.update({'mysticid': str(newObjectId)})
						itemsToInsert.append(toInsert)

						mysticsColOperations.append(pymongo.InsertOne(newMysticDoc))

			print(f'	readItems {int((time.time() - loopTimer) * 1000)}ms')

			playerDocAlready = database.playersCol.find_one({'_id': playerUuid})
			if playerDocAlready != None:
				if 'persist' in playerDocAlready:
					toUpsert['persist'] = playerDocAlready['persist']
					toUpsert['persist']['checkedpit'] = True

			checkPlayerDiffConstant = 1
			playerCheckAt = int(curTime + max(3600, (curTime - lastSave) / checkPlayerDiffConstant) * (0.9 + random.random() / 5))

			addToUpsert(playerCheckAt, 'checkat')

			print(f'	player last save was {util.prettyTimeStr(lastSave)}, checking again {util.prettyTimeStr(playerCheckAt)}')

			database.playersCol.replace_one({'_id': playerUuid}, toUpsert, upsert = True)
			util.addFlagToUuid(playerUuid, 'checkedpit', True) # REORGANIZE ? idk

			if len(itemsToInsert) > 0:
				database.itemsCol.insert_many(itemsToInsert)

			if len(mysticsColOperations) > 0:
				print(f'	doing mystic upserts for {len(mysticsColOperations)} mystics')
				database.mysticsCol.bulk_write(mysticsColOperations)
			else:
				print('		no mystics to upsert')

			print(f'	insertedItems {int((time.time() - loopTimer) * 1000)}ms')

		elif apiGot['success'] == False:
			print('	success false')
			if apiGot.get('cause') == 'Malformed UUID':
				print('	malformed UUID, deleting')
				database.playersCol.delete_one({'_id': playerUuid})
			elif apiGot.get('cause') == 'You have already looked up this name recently':
				print('	looked up too recently')
			else:
				print('	' + str(apiGot)[:64].replace('\n', ''))

				# why doesnt it have a 'cause'
				# turns out sometimes it just returns {'success': False} :shrug:
				# nevermind that was just being returned by getHypixelApi function

				if apiGot != {'success': False}: # would still like to see other errors
					discordsender.sendDiscord(f'indexPlayer noCause {str(apiGot)[:512]}', config.webhookUrlErrors)

def findUuids(apiData):
	uuidsList = []

	possibleRoutes = [['player', 'friendBlocksUuid'], ['player', 'friendRequests'], ['player', 'friendRequestsUuid'], ['player', 'mostRecentlyThankedUuid'], ['player', 'mostRecentlyTippedUuid'], ['player', 'stats', 'SkyWars', 'head_collection', 'recent'], ['player', 'stats', 'SkyWars', 'head_collection', 'prestigious']]

	def possibleUuid(checkUuid):
		if len(checkUuid) == 32:
			if checkUuid[12] == '4':
				uuidsList.append(checkUuid)
				util.addFlagToUuid(checkUuid, 'fromplayer', True)

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

	loopTimer = time.time()

	curTime = time.time()

	if random.randint(1, 256) == 1:
		print('	randomly adding panda leaderboard page')
		addPandaLeaderboardPage()
		return

	indexTypes = genIndexTypes()

	doneIndex = False

	for atQuery, (indexName, indexQuery) in enumerate(indexTypes.items()):

		if atQuery != len(indexTypes) - 1 and random.randint(1, 10) == 1: # random chance to just skip because i want it to pick which type somewhat randomly so that it favors the top index types but will also do the others sometimes even if there is a queue
			continue

		print(f'	checking {indexName}')
		foundDoc = database.playersCol.find_one(indexQuery)

		if foundDoc == None:
			print(f'	checked {indexName} {int((time.time() - loopTimer) * 1000)}ms')
			continue

		print(f'	foundDoc {int((time.time() - loopTimer) * 1000)}ms')
		docUuid = foundDoc['_id']

		print(f'indexing {docUuid} {indexName} indexedTimes = {int(len(indexedTimes))}')
		indexPlayer(docUuid)

		print(f'	finishedIndex {int((time.time() - loopTimer) * 1000)}ms')
		doneIndex = True

		indexerstats.incStat('indexedplayers')

		break

	indexedTimes.append(curTime)
	indexedTimes = list(filter(lambda x: x > curTime - 60, indexedTimes))

	print(f'	loopTimer {int((time.time() - loopTimer) * 1000)}ms')

	indexerstats.checkIfNeedToSaveStats()