import time
import logging

from flask import Flask
from flask_apscheduler import APScheduler

import indexer
import config

logging.getLogger('apscheduler').setLevel(logging.ERROR) # disable useless logs

apiQueriesThisMinute = 0
apiQueriesCurMinute = 0

pauseUntil = 0

secondsPerIndexerTask = 0.1
if config.debugMode:
	secondsPerIndexerTask = 99999

scheduler = APScheduler()

indexerQueue = []

def addToIndexerQueue(toAdd):
	indexerQueue.append(toAdd)

def indexerTask():
	global indexerQueue
	global apiQueriesThisMinute
	global apiQueriesCurMinute

	print(f'done {apiQueriesThisMinute} api queries this minute')

	curMinute = int(time.time() / 60)
	if curMinute != apiQueriesCurMinute:
		apiQueriesCurMinute = int(time.time() / 60)
		apiQueriesThisMinute = 0

	if apiQueriesThisMinute >= 120:
		return

	if time.time() < pauseUntil:
		return

	apiQueriesThisMinute += 1

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

scheduler.add_job(id = 'indexer task', func = indexerTask, trigger = "interval", seconds = secondsPerIndexerTask)
scheduler.start()