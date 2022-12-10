import os

import dotenv
dotenv.load_dotenv()

debugMode = False

if 'debug' in os.environ:
	debugMode = True
	print('running in DEBUG mode')
else:
	print('running in PRODUCTION mode')

mongoConnectString = os.environ['mongoconnectstring']

jojoKey = os.environ['jojokey']
noLimitKey = os.environ['nolimitkey']
hypixelApiKey = os.environ['hypixelapikey']
pitPandaApiKey = os.environ['pitpandaapikey']

webhookUrlMysticSearch = os.environ['webhookurlmysticsearch']
webhookUrlMystic = os.environ['webhookurlmystic']
webhookUrlOwnerHistory = os.environ['webhookurlownerhistory']
webhookUrlItemSearch = os.environ['webhookurlitemsearch']
webhookUrlItemImage = os.environ['webhookurlitemimage']