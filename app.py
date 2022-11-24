'''
terrible really bad code
dont know if i will bother to improve any of it as it just about works
enjoy
'''

print('init app')

import json
import time
import random
import requests
import os
import io
import re
import threading
import PIL
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageColor

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, session, send_from_directory, url_for, redirect, send_file
app = Flask(__name__)

webhookUrlSearches = os.environ['webhookurlsearches']
webhookUrlImages = os.environ['webhookurlimages']

jojoKey = os.environ['jojokey']
noLimitKey = os.environ['nolimitkey']
playersApiKey = os.environ['playersapikey']

debugMode = False
if 'debugmode' in os.environ:
	debugMode = True

import discordsender

print('connecting to db')
import pymongo
mongoConnectString = os.environ['mongoconnectstring']
dbClient = pymongo.MongoClient(mongoConnectString)
curDb = dbClient['hypixel']
playersCol = curDb['pitplayers']
itemsCol = curDb['pititems']
discordsCol = curDb['pitdiscords']
print('connected to db')

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
				saveStr = replaceColors(f'§8Seen in Pit {prettyDate(itemLastSave)}')
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

		itemsFound = map(itemFormat, itemsFound)

		return render_template('items.html', content = {'items': itemsFound, 'count': itemsFoundCount})
	except Exception as e:
		print(e)
		return 'error moment'

@app.route("/api/items/<path:page>", methods=['GET'])
def itemReqApi(page):
	try:
		curTime = time.time()

		fullUrl = request.path
		argsString = page.lower()
		argsList = argsString.split(',')

		if not debugMode:
			discordsender.sendDiscord(argsString, webhookUrlSearches)

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
					numFound = itemsCol.count_documents(dbQuery)
					print('counted')

					returnDict = {}
					returnDict['success'] = True
					returnDict['msg']   = 'counted'
					returnDict['count'] = numFound
					returnDict['items'] = []

					print(f'counted {numFound} items')

					return returnDict

			elif argKey == 'key':
				if argVal == jojoKey:
					if {'frompanda': True} in dbQueryAnds:
						dbQueryAnds.remove({'frompanda': True})
				if argVal == jojoKey + 'no':
					if {'frompanda': True} in dbQueryAnds:
						dbQueryAnds.remove({'frompanda': True})
					dbQueryAnds.append({'frompanda': {'$exists': False}})

				if argVal == noLimitKey or argVal == jojoKey:
					returnItemsLimit = 99999999999
			else:
				if argKey in enchNames:
					argKey = enchNames[argKey]
				dbQueryAnds.append({'enchpit':{'$elemMatch':{'Key': argKey, 'Level': {queryOperator: argNum}}}})

		if dbQueryAnds == [] or dbQueryAnds == [{'frompanda': True}]:
			foundItems = itemsCol.find({'$and': [{'frompanda': True}, {'tokens': 8}]}).limit(100) # default search for homepage
		else:
			dbQuery = {'$and': dbQueryAnds}

			foundItems = itemsCol.find(dbQuery).limit(returnItemsLimit + 1) # (bc idk if mongodb is actually aware whether it returned all the documents or the .limit actually kicked in so that's just detected below)

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

sentImages = {}
@app.route("/api/itemimage", methods=['GET'])
def itemImageRoute():

	# log

	if not debugMode and request.url not in sentImages:
		sentImages[request.full_path] = True
		discordsender.sendDiscord(request.full_path, webhookUrlImages)

	# get data

	textDelimiter = ',,,'

	itemLines = request.args.get('text', f'abc').split(textDelimiter)
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

				drawObj.text((atX + imageScale / 4, atLine * textSize + boxPadding + imageScale / 4), curChar, font = minecraftFontRegular, fill = tuple(map(lambda x: int(x / 4), curColor))) # shadow
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

cachedUuidsStr = 'null'
@app.route("/api/sendplayers", methods=['GET']) # sussy stuff
def sendPlayersApi():
	print('players sent')

	requestKey = request.headers.get('reqkey')

	if requestKey != playersApiKey:
		print('key wrong')
		return 'key wrong'

	uuidsStr = request.headers.get('uuids')

	if uuidsStr == None:
		print('no uuids string')
		return 'no uuids string'

	global cachedUuidsStr
	cachedUuidsStr = uuidsStr

	return 'success'

@app.route("/api/getplayers", methods=['GET'])
def getPlayersApi():
	print('players requested')

	requestKey = request.headers.get('reqkey')

	if requestKey != playersApiKey:
		print('key wrong')
		return 'key wrong'

	return cachedUuidsStr

@app.route("/api/checkdiscord/<discordId>", methods=['GET'])
def checkDiscordRoute(discordId):
	print('check discord')

	if not discordId.isnumeric():
		return {'success': False, 'uuid': None, 'message': 'invalid discord id - not numeric'}

	discordId = int(discordId)

	discordDoc = discordsCol.find_one({'_id': discordId})

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

def prettyDate(theTime):
	curTime = time.time()

	diffStr = f'ERROR <{theTime}>'

	timeDiff = theTime - curTime

	diffNum = 0
	if timeDiff > 0: # future
		if timeDiff < 1:
			diffNum = int(timeDiff)
			diffStr = f'right now'
		elif timeDiff < 60:
			diffNum = int(timeDiff)
			diffStr = f'in {diffNum} second[POTENTIALCHAR]'
		elif timeDiff < 60 * 60: # minutes
			diffNum = int(timeDiff / 60)
			diffStr = f'in {diffNum} minute[POTENTIALCHAR]'
		elif timeDiff < 60 * 60 * 24: # hours
			diffNum = int(timeDiff / 60 / 60)
			diffStr = f'in {diffNum} hour[POTENTIALCHAR]'
		elif timeDiff < 60 * 60 * 24 * 7: # days
			diffNum = int(timeDiff / 60 / 60 / 24)
			diffStr = f'in {diffNum} day[POTENTIALCHAR]'
		elif timeDiff < 60 * 60 * 24 * 30: # weeks
			diffNum = int(timeDiff / 60 / 60 / 24 / 7)
			diffStr = f'in {diffNum} week[POTENTIALCHAR]'
		elif timeDiff < 60 * 60 * 24 * 365: # months
			diffNum = int(timeDiff / 60 / 60 / 24 / 30)
			diffStr = f'in {diffNum} month[POTENTIALCHAR]'
		else: # years
			diffNum = int(timeDiff / 60 / 60 / 24 / 365)
			diffStr = f'in {diffNum} year[POTENTIALCHAR]'
	else: # past
		timeDiff = timeDiff * -1
		if timeDiff < 1:
			diffNum = int(timeDiff)
			diffStr = f'right now'
		elif timeDiff < 60:
			diffNum = int(timeDiff)
			diffStr = f'{diffNum} second[POTENTIALCHAR] ago'
		elif timeDiff < 60 * 60: # minutes
			diffNum = int(timeDiff / 60)
			diffStr = f'{diffNum} minute[POTENTIALCHAR] ago'
		elif timeDiff < 60 * 60 * 24: # hours
			diffNum = int(timeDiff / 60 / 60)
			diffStr = f'{diffNum} hour[POTENTIALCHAR] ago'
		elif timeDiff < 60 * 60 * 24 * 7: # days
			diffNum = int(timeDiff / 60 / 60 / 24)
			diffStr = f'{diffNum} day[POTENTIALCHAR] ago'
		elif timeDiff < 60 * 60 * 24 * 30: # weeks
			diffNum = int(timeDiff / 60 / 60 / 24 / 7)
			diffStr = f'{diffNum} week[POTENTIALCHAR] ago'
		elif timeDiff < 60 * 60 * 24 * 365: # months
			diffNum = int(timeDiff / 60 / 60 / 24 / 30)
			diffStr = f'{diffNum} month[POTENTIALCHAR] ago'
		else: # years
			diffNum = int(timeDiff / 60 / 60 / 24 / 365)
			diffStr = f'{diffNum} year[POTENTIALCHAR] ago'

	if diffNum > 1:
		diffStr = diffStr.replace('[POTENTIALCHAR]', 's')
	else:
		diffStr = diffStr.replace('[POTENTIALCHAR]', '')

	return diffStr