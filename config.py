import os

import dotenv
dotenv.load_dotenv()

debugMode = False

if 'debug' in os.environ:
	debugMode = True
	print('running in DEBUG mode')
else:
	print('running in PRODUCTION mode')

webhookUrlSearches = os.environ['webhookurlsearches']
webhookUrlImages = os.environ['webhookurlimages']

jojoKey = os.environ['jojokey']
noLimitKey = os.environ['nolimitkey']
playersApiKey = os.environ['playersapikey']
mongoConnectString = os.environ['mongoconnectstring']
hypixelApiKey = os.environ['hypixelapikey']