'''
terrible really bad code
dont know if i will bother to improve any of it as it just about works
enjoy
'''

print('init')

import json
import time
import random
import requests
import os

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, request, session, send_from_directory, url_for, redirect
app = Flask(__name__)

webhookUrl = os.environ['webhookurl']

jojoKey = os.environ['jojokey']

print('connecting')
import pymongo
mongoConnectString = os.environ['mongoconnectstring']
dbClient = pymongo.MongoClient(mongoConnectString)
curDb = dbClient['hypixel']
playersCol = curDb['pitplayers']
itemsCol = curDb['pititems']
print('connected')

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

		def itemFormat(itemTo):
			returnStr = ''

			if 'name' in itemTo:
				returnStr += replaceColors(itemTo['name']) + '<br>'
			else:
				if 'id' in itemTo:
					returnStr += 'Id: ' + replaceColors(itemTo['id']) + '<br>'
			if 'nonce' in itemTo:
				returnStr += f'<!-- Nonce: {itemTo["nonce"]} -->'
			returnStr += replaceColors('§8Owner: ' + itemTo['ownerusername'])
			if 'frompanda' not in itemTo:
				returnStr += ' <span style="color: #55FFFF"> [NOPANDA] </span>'
			saveStr = ''
			if 'lastsave' in itemTo:
				lastSaveHoursAgo = int((curTime - itemTo['lastsave']) / 60 / 60)
				lastSaveHoursAgo = min(999, lastSaveHoursAgo)
				saveStr = replaceColors(f'§8Seen in Pit {str(lastSaveHoursAgo)} hrs ago')
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

		sendDiscord(argsString)

		argsList = list(filter(lambda x: x != '', argsList))

		print(f'argsList {argsList}')

		dbQueryAnds = []
		dbQueryAnds.append({'frompanda': True}) # removed later if correct key

		for curArg in argsList:
			argSplit = curArg.split('=')

			#print(f'argSplit {argSplit}')

			argKey = argSplit[0]
			argVal = argSplit[1]

			if argVal == '':
				continue

			#print(f'argKey {argKey}')
			#print(f'argVal {argVal}')

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
			elif argKey == 'key':
				if argVal == jojoKey:
					dbQueryAnds.remove({'frompanda': True})
				if argVal == jojoKey + 'no':
					dbQueryAnds.remove({'frompanda': True})
					dbQueryAnds.append({'frompanda': {'$exists': False}})
			else:
				if argKey in enchNames:
					argKey = enchNames[argKey]
				dbQueryAnds.append({'enchpit':{'$elemMatch':{'Key': argKey, 'Level': {queryOperator: argNum}}}})

		if dbQueryAnds == [] or dbQueryAnds == [{'frompanda': True}]:
			foundItems = itemsCol.find({'$and': [{'frompanda': True}, {'tokens': 8}]}).limit(100) # default search for homepage
		else:
			dbQuery = {'$and': dbQueryAnds}

			foundItems = itemsCol.find(dbQuery).limit(1000)

		foundItemsList = []

		returnMsg = 'owo'

		numFound = 0
		for curItem in foundItems:
			if numFound >= 1000: # redundant due to .limit(1000)
				returnMsg = 'too many! first 1k given'
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

@app.route('/favicon.ico')
def favicon():
	return app.send_static_file('favicon.ico')

def sendDiscord(toSend):
	def sendDiscordPart(partToSend):
		url = webhookUrl
		data = {}
		data["username"] = "jojo.boats"
		data["content"] = partToSend
		requests.post(url, json=data, headers={"Content-Type": "application/json"}, timeout = 10)
	
	for i in range(int(len(toSend) / 2000) + 1):
		sendDiscordPart(toSend[i * 2000:i* 2000 + 2000])

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