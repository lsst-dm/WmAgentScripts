#!/usr/bin/env python

import urllib2,urllib, httplib, sys, re, os, json, phedexSubscription
from xml.dom.minidom import getDOMImplementation

def getWorkflowType(url, workflow):
	conn  =  httplib.HTTPSConnection(url, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request("GET",'/reqmgr/reqMgr/request?requestName='+workflow)
	r2=conn.getresponse()
	request = json.read(r2.read())
	requestType=request['RequestType']
	return requestType


def getRunWhitelist(url, workflow):
	conn  =  httplib.HTTPSConnection(url, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request("GET",'/reqmgr/reqMgr/request?requestName='+workflow)
	r2=conn.getresponse()
	request = json.read(r2.read())
	runWhitelist=request['RunWhitelist']
	return runWhitelist

def getBlockWhitelist(url, workflow):
	conn  =  httplib.HTTPSConnection(url, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request("GET",'/reqmgr/reqMgr/request?requestName='+workflow)
	r2=conn.getresponse()
	request = json.read(r2.read())
	BlockWhitelist=request['BlockWhitelist']
	return BlockWhitelist

def getInputDataSet(url, workflow):
	conn  =  httplib.HTTPSConnection(url, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request("GET",'/reqmgr/reqMgr/request?requestName='+workflow)
	r2=conn.getresponse()
	request = json.read(r2.read())
	inputDataSets=request['InputDataset']
	if len(inputDataSets)<1:
		print "No InputDataSet for workflow " +workflow
	else:
		return inputDataSets

def getEventsRun(url, dataset, run):
	output=os.popen("./dbssql --input='find dataset,sum(block.numevents) where dataset="+dataset+" and run="+str(run)+"' "+"|awk '{print $2}' | grep '[0-9]\{1,\}'").read()
	try:
		int(output)
		return int(output)
	except ValueError:
       		return -1	


def getEventCountDataSet(dataset):
	output=os.popen("./dbssql --input='find dataset,sum(block.numevents) where dataset="+dataset+"'"+ "|awk '{print $2}' | grep '[0-9]\{1,\}'").read()
	try:
		int(output)
		return int(output)
	except ValueError:
       		return -1

# SPlits a list of chunks of size(n)
def chunks(lis, n):
    return [lis[i:i+n] for i in range(0, len(lis), n)]



def getInputEvents(url, workflow):
	conn  =  httplib.HTTPSConnection(url, cert_file = os.getenv('X509_USER_PROXY'), key_file = os.getenv('X509_USER_PROXY'))
	r1=conn.request("GET",'/reqmgr/reqMgr/request?requestName='+workflow)
	r2=conn.getresponse()
	request = json.read(r2.read())
	requestType=request['RequestType']
	if requestType=='MonteCarlo':
		if 'RequestSizeEvents' in request:
			reqevts =request['RequestSizeEvents']
		elif 'RequestNumEvents' in request:
			reqevts =request['RequestNumEvents']
		else:
			reqevts=0
		return reqevts
	BlockWhitelist=request['BlockWhitelist']
	inputDataSet=request['InputDataset']
	runWhitelist=request['RunWhitelist']
	querry='find dataset,sum(block.numevents) where dataset='+inputDataSet
	if len(BlockWhitelist)>0:
		querry=querry+' AND ('
		for block in BlockWhitelist:
			querry=querry+' block= '+block+' OR'
		
		querry=querry+' block= '+BlockWhitelist[0] +')'
	if len(BlockWhitelist)>0 and len(BlockWhitelist)>10:
		events=0
		blockChunks=chunks(BlockWhitelist,10)
		for blockList in blockChunks:
			querry="./dbssql --input='find dataset,sum(block.numevents) where dataset="+inputDataSet+' AND ('
			for block in blockList:
				querry=querry+' block= '+block+' OR'
			querry=querry+' block= '+str(blockList[0]) +')'
			querry=querry+"'|awk '{print $2}' | grep '[0-9]\{1,\}'"
			output=os.popen(querry).read()
			try:
				events=events+int(output)
			except ValueError:
       				return -1
		if 'FilterEfficiency' in request.keys():
			return float(request['FilterEfficiency'])*int(events)
		else:
			return events
	if len(runWhitelist)>0:
		querry=querry+' AND ('
		for run in runWhitelist:
			querry=querry+' run= '+str(run)+' OR'
		
		querry=querry+' run= '+str(runWhitelist[0]) +')'
	if len(runWhitelist)>0 and len(runWhitelist)>30:
		events=0
		runChunks=chunks(runWhitelist,30)
		for runList in runChunks:
			querry="./dbssql --input='find dataset,sum(block.numevents) where dataset="+inputDataSet+' AND ('
			for run in runList:
				querry=querry+" run="+str(run) +" OR "
			querry=querry+' run= '+str(runList[0]) +')'
			querry=querry+"'|awk '{print $2}' | grep '[0-9]\{1,\}'"
			output=os.popen(querry).read()
			if not output:
				output=0
			try:
				events=events+int(output)
			except ValueError:
       				return -1
		return events
	else:
		output=os.popen("./dbssql --input='"+querry+"'"+ "|awk '{print $2}' | grep '[0-9]\{1,\}'").read()
	try:
		int(output)
		if 'FilterEfficiency' in request.keys():
			return float(request['FilterEfficiency'])*int(output)
		else:
			return int(output)
	except ValueError:
       		return -1
	
def main():
	args=sys.argv[1:]
	if not len(args)==1:
		print "usage:dbsTest workflowname"
		sys.exit(0)
	workflow=args[0]
	url='cmsweb.cern.ch'
	outputDataSets=phedexSubscription.outputdatasetsWorkflow(url, workflow)
	inputEvents=getInputEvents(url, workflow)
#	print "number of input events: "+str(inputEvents)
	for dataset in outputDataSets:
		outputEvents=getEventCountDataSet(dataset)
		if inputEvents==0:
			print "Input Events: 0"
			sys.exit(0);
		print dataset+" match: "+str(outputEvents/float(inputEvents)*100) +"%"
	sys.exit(0);

if __name__ == "__main__":
	main()

