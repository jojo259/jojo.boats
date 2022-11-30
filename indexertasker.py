from flask import Flask
from flask_apscheduler import APScheduler

import indexer

secondsPerIndexerTask = 5

scheduler = APScheduler()

indexerQueue = []

def addToIndexerQueue(toAdd):
	indexerQueue.append(toAdd)

def indexerTask():
	global indexerQueue

	print('doing indexer task')

	if len(indexerQueue) > 0:
		print('indexing queued player')
		curQueued = indexerQueue[0]
		indexerQueue = indexerQueue[1:]
		indexer.indexPlayer(curQueued)
	else:
		print('doing regular indexer loop')
		indexer.doLoop()

	print('done indexer task')

scheduler.add_job(id = 'Scheduled Task', func=indexerTask, trigger="interval", seconds=secondsPerIndexerTask)
scheduler.start()