import time

import database
import discordsender

saveStatsIntervalSeconds = 5

indexerStatsTypes = [
	'indexedplayers',
	'ownerchanges',
	'gemmed',
	'upgradedtotier1',
	'upgradedtotier2',
	'upgradedtotier3',
	'newregularmystic',
]

indexerStatsInc = {}

lastSavedStats = time.time()

def resetIndexerStatsInc():

	global indexerStatsInc

	for curType in indexerStatsTypes:
		indexerStatsInc[curType] = 0

def checkIfNeedToSaveStats():

	global lastSavedStats

	curTime = time.time()

	if curTime - lastSavedStats > saveStatsIntervalSeconds:

		lastSavedStats = max(lastSavedStats + saveStatsIntervalSeconds, curTime - saveStatsIntervalSeconds * 2)
		saveStats()

def incStat(statToInc, incAmount = 1):

	global indexerStatsTypes

	if statToInc not in indexerStatsTypes:
		discordsender.sendDiscord(f'tried to inc unknown stat type {statToInc} by {incAmount}', config.webhookUrlErrors)
		return

	indexerStatsInc[statToInc] += 1

def saveStats():

	print('saving indexer stats')

	hourNum = int(time.time() / 3600)

	database.indexerStatsCol.update_one({'_id': hourNum}, {'$inc': indexerStatsInc}, upsert = True)
	resetIndexerStatsInc()

resetIndexerStatsInc()