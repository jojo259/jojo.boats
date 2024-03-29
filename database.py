import config

print('connecting to db')
import pymongo
dbClient = pymongo.MongoClient(config.mongoConnectString)
curDb = dbClient['hypixel']
playersCol = curDb['pitplayers']
itemsCol = curDb['pititems']
mysticsCol = curDb['pitmystics']
discordsCol = curDb['pitdiscords']
indexerStatsCol = curDb['indexerstats']
notableMessagesCol = curDb['notablemessages']
friendsCol = curDb['friends']
print('connected to db')