'''
terrible really bad code
dont know if i will bother to improve any of it as it just about works
enjoy
'''

print('init')

import json
import time
import datetime
import random
import requests
from dateutil import parser
import os
import io
import re
import threading
import urllib
import math
import PIL
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageColor

from dotenv import load_dotenv
load_dotenv()

import bson

from flask import Flask, render_template, request, session, send_from_directory, url_for, redirect, send_file
app = Flask(__name__)

import config
import discordsender
import database
import indexer
import indexertasker
if not config.debugMode: # websocket prevents keyboard interrupts. annoying af
	import pandasocket

enchNames = {}
with open("enchnames.txt") as enchNamesFile:
	enchNamesFile = enchNamesFile.read()
	for curLine in enchNamesFile.split("\n"):
		curLineSplit = curLine.split(" ")
		enchNames[curLineSplit[0]] = curLineSplit[1]

@app.route('/')
def mainPage():
	return redirect('items/search')

@app.route("/search", methods=['GET', 'POST'])
def itemReqSearch():
	try:
		searchData = request.form.to_dict().items()

		print()
		print('inside /search')

		print(f'searchData {searchData}')

		argsString = ','.join(list(filter(None, map(lambda x: None if x[1] == '' else x[0] + '=' + x[1], list(searchData)))))

		redirectUrl = '/items/search?' + argsString

		print(f'redirecting {redirectUrl}')

		return redirect(redirectUrl)
	except Exception as e:
		print(e)
		return 'error moment'

@app.route("/items/")
def itemPagePlain():
	return render_template('items.html', content = {'items': [], 'count': 0})

@app.route("/items/<path:page>", methods=['GET', 'POST'])
def itemReq(page):
	try:
		fullUrl = request.full_path

		print()
		print(f'fullUrl {fullUrl}')

		argsString = fullUrl.split('?')[1]

		print(f'argsString {argsString}')

		itemsReq = itemReqApi(argsString)

		itemsFound = itemsReq['items']
		itemsFoundCount = itemsReq['count']

		curTime = time.time()

		def itemFormat(itemTo): # me when i manually construct html
			returnStr = ''

			if 'name' in itemTo:
				returnStr += replaceColors(itemTo['name']) + '<br>'
			else:
				if 'id' in itemTo:
					returnStr += 'Id: ' + replaceColors(itemTo['id']) + '<br>'
			if 'nonce' in itemTo:
				returnStr += f'<!-- Nonce: {itemTo["nonce"]} -->'

			# damn this surrounding code is soooooo dumb
			returnStr += f'<!-- UUID: {itemTo.get("owner")} -->'

			returnStr += replaceColors('§8Owner: ' + itemTo['ownerusername'])
			if 'frompanda' not in itemTo:
				returnStr += ' <span style="color: #55FFFF"> [NOPANDA] </span>'
			saveStr = ''
			if 'lastsave' in itemTo:
				itemLastSave = itemTo['lastsave']
				saveStr = replaceColors(f'§8Seen in Pit {prettyTimeStr(itemLastSave)}')
				#saveStr = str(itemTo['lastsave'])
			if 'lore' in itemTo:
				returnStr += '<br>'
				addedLastSave = False
				for lineAt, curLore in enumerate(itemTo['lore']):
					if lineAt == 0 and curLore == '':
						returnStr += '<br>'
						continue
					if lineAt == 1:
						returnStr += saveStr + '<br>'
						continue
					returnStr += replaceColors(curLore) + '<br>'

			returnStr += '</span>'

			return {'text': returnStr}

		""" would probably take up all of the indexer's time
		for curItem in itemsFound:
			itemOwner = curItem.get('owner')
			if itemOwner != None:
				indexertasker.addToIndexerQueue(itemOwner)
		"""

		itemsFound = map(itemFormat, itemsFound)

		return render_template('items.html', content = {'items': itemsFound, 'count': itemsFoundCount})
	except Exception as e:
		print(e)
		return 'error moment'

@app.route("/api/addtoindexerqueue/<playerTag>", methods=['GET'])
def addToIndexerQueueRoute(playerTag):
	indexertasker.addToIndexerQueue(playerTag)
	return {'success': True, 'message': 'added'}

@app.route("/api/items/<path:page>", methods=['GET'])
def itemReqApi(page):
	try:
		curTime = time.time()

		fullUrl = request.path
		argsString = page.lower()
		argsList = argsString.split(',')

		if not config.debugMode:
			discordsender.sendDiscord(argsString, config.webhookUrlItemSearch)

		argsList = list(filter(lambda x: x != '', argsList))

		print(f'argsList {argsList}')

		dbQueryAnds = []
		dbQueryAnds.append({'frompanda': True}) # removed later if correct key

		returnItemsLimit = 1000

		for curArg in argsList:
			argSplit = curArg.split('=')

			argKey = argSplit[0]
			argVal = argSplit[1]

			if argVal == '':
				continue

			argVal = argVal.replace('%2B', '+')
			argVal = argVal.replace('%20', ' ')

			if argKey == 'enchant1' or argKey == 'enchant2' or argKey == 'enchant3':
				lastChar = argVal[-1]
				if lastChar.isnumeric() or lastChar == '+' or lastChar == '-':
					lastLastChar = argVal[-2]
					if lastLastChar.isnumeric():
						argVal = argVal[:-2] + ' ' + argVal[-2] + argVal[-1]
					else:
						argVal = argVal[:-1] + ' ' + argVal[-1]
					argValSplit = argVal.split()
					argKey = argValSplit[0]
					argVal = argValSplit[1]
				else:
					argKey = argVal
					argVal = '0+'

			queryOperator = '$eq'

			keyLastChar = argVal[-1]
			if keyLastChar == '+':
				queryOperator = '$gte'
				argVal = argVal[:-1]
			elif keyLastChar == '-':
				queryOperator = '$lte'
				argVal = argVal[:-1]

			if argVal.isnumeric():
				argNum = int(argVal)

			if argKey == 'name':
				dbQueryAnds.append({'nameclean': argVal})
			elif argKey == 'owner':
				dbQueryAnds.append({'owner': argVal})
			elif argKey in ('nonce', 'id', 'lives', 'maxlives', 'tier', 'tokens'):
				dbQueryAnds.append({argKey: {queryOperator: argNum}})
			elif argKey == 'gemmed':
				if argVal == 'false':
					dbQueryAnds.append({'gemmed': {'$exists': False}})
				elif argVal == 'true':
					dbQueryAnds.append({'gemmed': True})
			elif argKey == 'maxhours':
				dbQueryAnds.append({'lastsave': {'$gt': curTime - argNum * 3600}})
			elif argKey == 'minhours':
				dbQueryAnds.append({'lastsave': {'$lt': curTime - argNum * 3600}})
			elif argKey == 'haslore':
				if argVal == 'true':
					dbQueryAnds.append({'lore': {'$exists': True}})
				else:
					dbQueryAnds.append({'lore': {'$exists': False}})
			elif argKey == 'limit':
				returnItemsLimit = min(returnItemsLimit, int(argVal))

			elif argKey == 'count': # special count logic

				if argVal == 'true':
					if {'frompanda': True} in dbQueryAnds:
						dbQueryAnds.remove({'frompanda': True})
					dbQuery = {'$and': dbQueryAnds}

					print('counting')
					numFound = database.itemsCol.count_documents(dbQuery)
					print('counted')

					returnDict = {}
					returnDict['success'] = True
					returnDict['msg']   = 'counted'
					returnDict['count'] = numFound
					returnDict['items'] = []

					print(f'counted {numFound} items')

					return returnDict

			elif argKey == 'key':
				if argVal == config.jojoKey:
					if {'frompanda': True} in dbQueryAnds:
						dbQueryAnds.remove({'frompanda': True})
				if argVal == config.jojoKey + 'no':
					if {'frompanda': True} in dbQueryAnds:
						dbQueryAnds.remove({'frompanda': True})
					dbQueryAnds.append({'frompanda': {'$exists': False}})

				if argVal == config.noLimitKey or argVal == config.jojoKey:
					returnItemsLimit = 99999999999
			else:
				if argKey in enchNames:
					argKey = enchNames[argKey]
				dbQueryAnds.append({'enchpit':{'$elemMatch':{'Key': argKey, 'Level': {queryOperator: argNum}}}})

		if dbQueryAnds == [] or dbQueryAnds == [{'frompanda': True}]:
			foundItems = database.itemsCol.find({'$and': [{'frompanda': True}, {'tokens': 8}]}).limit(100) # default search for homepage
		else:
			dbQuery = {'$and': dbQueryAnds}

			foundItems = database.itemsCol.find(dbQuery).limit(returnItemsLimit + 1) # (bc idk if mongodb is actually aware whether it returned all the documents or the .limit actually kicked in so that's just detected below)

		foundItemsList = []

		returnMsg = 'owo'

		numFound = 0
		for curItem in foundItems:
			if numFound >= returnItemsLimit: # ^ read above
				returnMsg = f'too many! first {numFound} items given'
				break
			curItem['_id'] = str(curItem['_id'])
			foundItemsList.append(curItem)

			numFound += 1

		returnDict = {}
		returnDict['success'] = True
		returnDict['msg']   = returnMsg
		returnDict['count'] = numFound
		returnDict['items'] = foundItemsList

		print(f'returning {numFound} items')

		return returnDict
	except Exception as e:
		print(e)
		returnDict = {}
		returnDict['success'] = False
		returnDict['msg'] = 'fatal error ggs'

		return returnDict

@app.route("/api/mysticsearch/<queryStr>", methods=['GET'])
def mysticSearchRoute(queryStr):

	print(f'mysticSearchRoute')

	if not config.debugMode:
		discordsender.sendDiscord(queryStr, config.webhookUrlMysticSearch)
	
	requestParams = queryStr.split(',')

	print(f'	request params: {requestParams}')

	def getEnchantKeyValueOperator(fromStr):
		strKey = fromStr
		strVal = ''
		strOperator = '$eq'

		if strKey[-1] in ('+', '-'):
			if strKey[-1] == '+':
				strOperator = '$gte'
			elif strKey[-1] == '-':
				strOperator = '$lte'
			strKey = strKey[:-1]

		if strKey[-1].isnumeric():
			while strKey[-1].isnumeric():
				strVal = str(strKey[-1]) + str(strVal)
				strKey = strKey[:-1]
		else:
			strVal = 0
			strOperator = '$gte'

		strVal = int(strVal)

		return strKey, strVal, strOperator

	dbQueryAnds = [{'item.frompanda': True}]

	for curParam in requestParams:

		# check for the MOST special param, gemmed, which has a boolean value

		if curParam in ('gemmed', '!gemmed'):

			print(f'	curParam gemmed {curParam}')
			
			if curParam == 'gemmed':
				dbQueryAnds.append({'item.gemmed': True})
			elif curParam == '!gemmed':
				dbQueryAnds.append({'item.gemmed': {'$exists': False}})

			continue

		# check for the SECOND most special param, owner, which has a string value

		if curParam.startswith('uuid') or curParam.startswith('owner'):

			print(f'	curParam owner {curParam}')
			dbQueryAnds.append({'item.owner': curParam.replace('uuid', '').replace('owner', '')}) # (works..)
			continue

		# next check for the special params, which have number values

		paramKey, paramVal, paramOperator = getEnchantKeyValueOperator(curParam)

		if paramKey.startswith('maxlives'):

			print(f'	curParam maxlives {curParam}')
			dbQueryAnds.append({'item.maxlives': {paramOperator: paramVal}})
			continue

		# now we have to assume it is an enchant param, which also uses number values but can be any key (hopefully it is an enchant)

		print(f'	curParam enchant {curParam}')
		if paramKey in enchNames.keys():
			paramKey = enchNames[paramKey]
		dbQueryAnds.append({'item.enchpit':{'$elemMatch':{'Key': paramKey, 'Level': {paramOperator: paramVal}}}})

	mysticsFound = list(database.mysticsCol.find({'$and': dbQueryAnds}, {'owners': 0, 'tier1': 0, 'tier2': 0, 'item.lore': 0, 'item.name': 0, 'item.lastsave': 0, 'item.frompanda': 0}))

	for curMystic in mysticsFound:
		prettifyMysticId(curMystic)

	mysticsFound.update({'success': True})

	return mysticsFound

@app.route("/api/mystic/<mysticId>", methods=['GET'])
def getMysticRoute(mysticId):

	print('getMysticRoute')

	if not config.debugMode:
		discordsender.sendDiscord(mysticId, config.webhookUrlMystic)

	if len(mysticId) != 24:
		return {'success': False, 'msg': 'invalid bson object id, not 24 characters'}

	foundMystic = database.mysticsCol.find_one({'_id': bson.ObjectId(mysticId)})

	if foundMystic == None:
		return {'success': False, 'msg': 'mystic id not found'}

	if foundMystic.get('item', {}).get('frompanda') != True:
		return {'success': False, 'msg': 'mystic not in pitpanda db'}

	foundMystic.update({'success': True})
	prettifyMysticId(foundMystic)

	return foundMystic

@app.route("/api/ownerhistory/<mysticId>", methods=['GET'])
def ownerHistoryRoute(mysticId):

	print('ownerHistoryRoute')

	if not config.debugMode:
		discordsender.sendDiscord(mysticId, config.webhookUrlOwnerHistory)

	if len(mysticId) != 24:
		return {'success': False, 'msg': 'invalid bson object id, not 24 characters'}

	foundMystic = database.mysticsCol.find_one({'_id': bson.ObjectId(mysticId)})

	if foundMystic == None:
		return {'success': False, 'msg': 'mystic id not found'}

	if foundMystic.get('item', {}).get('frompanda') != True:
		return {'success': False, 'msg': 'mystic not in pitpanda db'}
	
	foundMysticOwner = foundMystic.get('item', {}).get('owner', '')
	foundMysticEnchants = foundMystic.get('item', {}).get('enchpit', [])

	pitPandaQueryStr = f'uuid{foundMysticOwner}'

	if len(foundMysticEnchants) > 0:
		for curEnch in foundMysticEnchants:
			pitPandaQueryStr += ',' + curEnch.get('Key') + str(curEnch.get('Level'))

	pitPandaMysticSearchApiUrl = f'https://pitpanda.rocks/api/itemsearch/{pitPandaQueryStr}?key={config.pitPandaApiKey}'
	try:
		pitPandaMysticSearchApiGot = requests.get(pitPandaMysticSearchApiUrl, timeout = 30).json()
	except Exception as e:
		print(f'pitPandaMysticSearchApiGot failed {e}')
	pitPandaMysticSearchApiItems = pitPandaMysticSearchApiGot.get('items', [])

	pitPandaOwnerHistory = []

	if len(pitPandaMysticSearchApiItems) == 1:

		pitPandaItemId = pitPandaMysticSearchApiItems[0].get('id')

		pitPandaItemApiUrl = f"https://pitpanda.rocks/api/item/{pitPandaItemId}?key={config.pitPandaApiKey}"
		try:
			pitPandaItemApiGot = requests.get(pitPandaItemApiUrl, timeout = 30).json()
		except Exception as e:
			pitPandaOwnerHistory = []
			print(f'pitPandaItemApiGot failed {e}')

		pitPandaOwnerHistory = pitPandaItemApiGot.get('item', {}).get('owners', [])

	newOwnerHistory = foundMystic.get('owners', [])

	for curPandaOwnerData in pitPandaOwnerHistory:
		curPandaTime = parseTimestamp(curPandaOwnerData.get('time'))
		newOwnerHistory.append({'uuid': curPandaOwnerData.get('uuid'), 'first': curPandaTime, 'last': curPandaTime})

	newOwnerHistory.sort(key = lambda x: x['first'])

	for atOwnerData in range(len(newOwnerHistory) - 1, 0, -1):
		if newOwnerHistory[atOwnerData - 1]['uuid'] == newOwnerHistory[atOwnerData]['uuid']:
			newOwnerHistory[atOwnerData - 1]['last'] = newOwnerHistory[atOwnerData]['last']
			newOwnerHistory.pop(atOwnerData)

	if False: # for debugging
		for curData in newOwnerHistory:
			timestampStr = '%Y/%m/%d - %H:%M:%S'
			curData['first'] = datetime.datetime.fromtimestamp(curData['first']).strftime(timestampStr)
			curData['last'] = datetime.datetime.fromtimestamp(curData['last']).strftime(timestampStr)

	return {'success': True, 'ownerhistory': newOwnerHistory}

sentImages = {}
@app.route("/api/itemimage", methods=['GET'])
def itemImageRoute():

	"""
		takes as query params:
		text
		OR
		(name AND (lore/desc/description))
		OR
		raw hypixel item nbt json
		OR
		item json with name and lore/desc/description fields (pitpanda, jojoboats)
	"""

	# log

	if not config.debugMode and request.url not in sentImages:
		sentImages[request.full_path] = True
		discordsender.sendDiscord(urllib.parse.unquote(request.full_path), config.webhookUrlItemImage)

	# get data

	argsName = request.args.get('name')
	argsLore = request.args.get('lore') or request.args.get('desc') or request.args.get('description')
	argsText = request.args.get('text')
	argsItemJson = request.args.get('itemjson')

	if argsItemJson != None:
		itemJson = json.loads(argsItemJson)

		argsName = itemJson.get('tag', {}).get('display', {}).get('Name')
		argsLore = itemJson.get('tag', {}).get('display', {}).get('Lore')

		if argsName == None or argsLore == None:
			# pitpand/jojoboats/other processed item data
			argsName = itemJson.get('name')
			argsLore = ',,,'.join(itemJson.get('lore') or itemJson.get('desc') or itemJson.get('description'))

	itemTextRaw = 'abc'

	if argsText != None:
		itemTextRaw = argsText

	if argsName != None and argsLore != None:
		itemTextRaw = argsName + ',,,' + argsLore

	itemLines = itemTextRaw.split(',,,')

	imageScale = request.args.get('scale') # minimum 4 for 1 pixel per minecraft font pixel, prob 8 recommended (multiples of 4 to match the minecraft font pixels)

	if imageScale == None:
		imageScale = 8
	else:
		imageScale = int(imageScale)

	# data

	maxImageSize = imageScale * 128 # idk that's like 4k i guess

	textSize = 3 * imageScale
	boxPadding = imageScale

	minecraftFontRegular = ImageFont.truetype('static/MinecraftRegular.otf', textSize)
	minecraftFontBold = ImageFont.truetype('static/MinecraftBold.otf', textSize)
	minecraftFontItalic = ImageFont.truetype('static/MinecraftItalic.otf', textSize)
	minecraftFontBoldItalic = ImageFont.truetype('static/MinecraftBoldItalic.otf', textSize)

	# create image, mildly yoinked from https://github.com/PitPanda/PitPandaProduction/blob/master/imageApi/index.js

	itemImage = PIL.Image.new('RGB', (maxImageSize, maxImageSize), color = (18, 2, 17))
	drawObj = ImageDraw.Draw(itemImage)

	imageWidth = min(maxImageSize, boxPadding * 2 + max(list(map(lambda curLine: drawObj.textlength(re.sub(r'§.', '', curLine), font = minecraftFontRegular), itemLines))))
	imageHeight = min(maxImageSize, len(itemLines) * textSize + boxPadding * 2)
	itemImage = itemImage.crop((0, 0, imageWidth, imageHeight))
	drawObj = ImageDraw.Draw(itemImage) # kinda lost but whatever

	# item outline

	outlineWidth = 8
	drawObj.rectangle([(0, 0), (imageWidth - 1, imageHeight - 1)], outline = (37, 1, 91), width = int(imageScale / 4))

	# text

	for atLine, curLine in enumerate(itemLines):
		curColor = (170, 170, 170)
		atX = boxPadding

		for curWord in curLine.split(' '):

			curWord = curWord + ' ' # add back missing space from split and add placeholder white color code

			atColorCode = False

			for curChar in curWord: # too lazy to not just go char by char

				if curChar == '❤':
					curChar = '♥' # ascii heart instead of emoji

				# check for color code

				if curChar == '§':
					atColorCode = True
					continue

				if atColorCode:
					atColorCode = False
					minecraftColorCodes = {'4': '#AA0000', 'c': '#FF5555', '6': '#FFAA00', 'e': '#FFFF55', '2': '#00AA00', 'a': '#55FF55', 'b': '#55FFFF', '3': '#00AAAA', '1': '#0000AA', '9': '#5555FF', 'd': '#FF55FF', '5': '#AA00AA', 'f': '#FFFFFF', '7': '#AAAAAA', '8': '#555555', '0': '#000000'}
					curColor = ImageColor.getcolor(minecraftColorCodes.get(curChar, '#CCC'), 'RGB')
					continue

				pixelScaleConst = 0.296875 # idek why

				drawObj.text((atX + imageScale * pixelScaleConst, atLine * textSize + boxPadding + imageScale * pixelScaleConst), curChar, font = minecraftFontRegular, fill = tuple(map(lambda x: int(x / 4), curColor))) # shadow
				drawObj.text((atX, atLine * textSize + boxPadding), curChar, font = minecraftFontRegular, fill = curColor)
				atX += drawObj.textlength(curChar, font = minecraftFontRegular)

	return serve_pil_image(itemImage)

def serve_pil_image(pil_img): # https://stackoverflow.com/a/51986716
    img_io = io.BytesIO()
    pil_img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route("/kos", methods=['GET'])
def kosPage():
	return render_template('kos.html')

pandaCache = {}
@app.route("/api/panda", methods=['GET'])
def pandaApi():
	curTime = time.time()

	pandaUrl = request.headers.get('pandaurl')

	print(f'getting {pandaUrl}')

	if pandaUrl == None:
		return {'success': False, 'message': 'no panda url provided under header pandaurl e.g. https://pitpanda.rocks/api/itemsearch/melee_literally_p2w0+'}

	if not pandaUrl.startswith('https://pitpanda.rocks/api/'):
		return {'success': False, 'message': 'url is not for pit panda api, doesnt start with https://pitpanda.rocks/api/'}

	if pandaUrl in pandaCache:
		if pandaCache[pandaUrl]["time"] > curTime - 60 * 60 * 24:
			print("returning cached request")
			return pandaCache[pandaUrl]["data"]
		else:
			print("deleting cached request")
			pandaCache.pop(pandaUrl)

	try:
		print(f'requesting')
		pandaApiGot = requests.get(pandaUrl, timeout = 5).json()
	except:
		print('probably timed out')
		return {'success': False, 'message': 'probably timed out'}

	if pandaApiGot['success']:
		pandaCache[pandaUrl] = {"time": curTime, "data": pandaApiGot}

	print('returning api got')

	return pandaApiGot

playersAdded = []
@app.route(f"/api/{config.jojoKey}/addplayer/<playerTag>", methods=['GET'])
def addPlayerRoute(playerTag):
	global playersAdded

	print(f'add player route')

	if playerTag in playersAdded:
		print(f'	already added {playerTag}')
		return {'success': True, 'msg': 'already added'}

	playersAdded.append(playerTag)
	if len(playersAdded) > 4096:
		playersAdded = playersAdded[2048:]

	database.playersCol.update_one({'_id': playerTag}, {'$set': {'persist.checkedpit': False}}, upsert = True)

	print(f'	upserted {playerTag}')

	return {'success': True, 'msg': 'added'}

@app.route(f"/api/{config.jojoKey}/pauseindexer/<extraPauseHours>", methods=['GET'])
def pauseIndexerRoute(extraPauseHours):
	print(f'pause indexer route')

	newPauseUntil = time.time() + int(extraPauseHours) * 3600

	print(f'	pausing indexer until {newPauseUntil}')

	indexertasker.pauseUntil = newPauseUntil
	return {'success': True, 'newpauseuntil': newPauseUntil}

@app.route("/api/checkdiscord/<discordId>", methods=['GET'])
def checkDiscordRoute(discordId):
	print('check discord')

	if not discordId.isnumeric():
		return {'success': False, 'uuid': None, 'message': 'invalid discord id - not numeric'}

	discordId = int(discordId)

	discordDoc = database.discordsCol.find_one({'_id': discordId})

	if discordDoc == None:
		return {'success': True, 'uuid': None, 'message': 'no user found'}

	playerUuid = discordDoc.get('uuid')
	playerMaybeUsername = discordDoc.get('username', '')

	playerMutualServers = len(discordDoc.get('guilds', []))

	return {'success': True, 'uuid': playerUuid, 'maybeusername': playerMaybeUsername, 'abyssbotmutualservers': playerMutualServers, 'message': 'found user'}

@app.route("/api/enchnames", methods=['GET'])
def enchNamesApi():
	return json.dumps(enchNames)

@app.route('/favicon.ico')
def favicon():
	return app.send_static_file('favicon.ico')

def prettifyMysticId(curItem):
	curItem['mysticid'] = str(curItem.get('_id'))
	curItem.pop('_id')

def parseTimestamp(curTimestamp):
	return int(parser.parse(curTimestamp).timestamp())

def replaceColors(repStr):
	try:
		repStr = str(repStr)

		colorList = {'o': 'font-style: italic', 'm': '"text-decoration: line-through', 'm': 'text-decoration: underline', 'l': 'font-weight: bold', '4': 'color: #AA0000', 'c': 'color: #FF5555', '6': 'color: #FFAA00', 'e': 'color: #FFFF55', '2': 'color: #00AA00', 'a': 'color: #55FF55', 'b': 'color: #55FFFF', '3': 'color: #00AAAA', '1': 'color: #0000AA', '9': 'color: #5555FF', 'd': 'color: #FF55FF', '5': 'color: #AA00AA', 'f': 'color: #FFFFFF', '7': 'color: #AAAAAA', '8': 'color: #555555', '0': 'color: #000000'}

		lastBad = False
		spanOn = False
		newStr = ''
		repStrLen = len(repStr)
		for i in range(repStrLen): # <span style="color: blue"> </span>
			if not lastBad:
				curChar = repStr[i]
				if curChar == '§' and spanOn == False:
					lastBad = True
					spanOn = True
					try:
						newStr += f'<span style="{colorList[repStr[i + 1]]}">'
					except:
						newStr += f'<span style="color: red">?MISSINGCOL?{repStr[i + 1]}'
				elif curChar == '§' and spanOn == True:
					lastBad = True
					newStr += '</span>'
					try:
						newStr += f'<span style="{colorList[repStr[i + 1]]}">'
					except:
						newStr += f'<span style="color: red">?MISSINGCOL?{repStr[i + 1]}'
				else:
					newStr += curChar
			else:
				lastBad = False
			if i == repStrLen - 1 and spanOn:
				newStr += '</span>'
		return newStr
	except Exception as e:
		print(e)
		return ''

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