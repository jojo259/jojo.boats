import time
import logging

from flask import Flask
from flask_apscheduler import APScheduler

import indexer
import config

logging.getLogger('apscheduler').setLevel(logging.ERROR) # disable useless logs

pauseUntil = 0

secondsPerIndexerTask = 0.5
if config.debugMode:
	secondsPerIndexerTask = 99999

scheduler = APScheduler()

indexerQueue = []

def addToIndexerQueue(toAdd):
	indexerQueue.append(toAdd)

def indexerTask():
	global indexerQueue

	if time.time() < pauseUntil:
		return

	print('doing indexer task')

	if len(indexerQueue) > 0:
		indexerQueue = list(dict.fromkeys(indexerQueue)) # remove duplicates
		curQueued = indexerQueue[0]
		indexerQueue = indexerQueue[1:]
		print(f'indexing queued player {curQueued}')
		indexer.indexPlayer(curQueued)
	else:
		print('doing regular indexer loop')
		indexer.doLoop()

	print('done indexer task')

scheduler.add_job(id = 'Scheduled Task', func=indexerTask, trigger="interval", seconds=secondsPerIndexerTask)
scheduler.start()