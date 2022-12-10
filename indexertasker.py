import time

from flask import Flask
from flask_apscheduler import APScheduler

import indexer
import config

pauseUntil = 0

secondsPerIndexerTask = 0.5 # will error like crazy if each task takes too long but whatever doesn't cause any issues "maximum number of running instances reached"
if config.debugMode:
	secondsPerIndexerTask = 10

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