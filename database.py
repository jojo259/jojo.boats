import config

print('connecting to db')
import pymongo
dbClient = pymongo.MongoClient(config.mongoConnectString)
curDb = dbClient['hypixel']
playersCol = curDb['pitplayers']
itemsCol = curDb['pititems']
discordsCol = curDb['pitdiscords']
print('connected to db')