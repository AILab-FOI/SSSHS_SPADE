#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import division
import operator
from time import sleep, gmtime, strftime
import matplotlib.pyplot as plt
import subprocess
import sys
from multiprocessing import Process
#import threading

from spade.Agent import BDIAgent
from spade.Behaviour import OneShotBehaviour, EventBehaviour, ACLTemplate, MessageTemplate
from spade.ACLMessage import ACLMessage
from spade.AID import aid
from spade.SWIKB import SWIKB as KB



Overflow = 0.00

sim_time = 3
callbacks = []
timer = 1
agents = []
agentNames = []
storages = []
storageNames = []
agentStorage = {}
allConsumption = []
allProduction = []
lowestCRLstorages = []

Overflow = 0
totalInterventions = 0 # Total number of system interventions. If the number is "fairly big", the system needs architectural changes.
firstIntervention = 0 # Time unit in which the first system intervention happened.
interventionTimes = [] # a list of time units in which interventions happened
economyRequests = 0 # A total number of economy requests
delayRequests = 0 # A total number of delay requests
restoreEconomyRequests = 0
advanceRequests = 0
giveRequests = 0
negotiationRequests = 0
UTalerts = 0 # upper threshold alerts
LTalerts = 0 # lower threshold alerts


def startSimulation():

	time = strftime("%d.%m.%Y %H:%M:%S", gmtime())

	print("\n\n\n*********** SIMULATION START ***********")
	print("****** TIME: %s *******" %time)

	for s in storages:
		storageNames.append(s.storageName)

	print ("****** Units in the system %s" %storageNames)


	i=0
	global timer
	while timer <= sim_time:

		print ("\n \n \n \n ---------------- Now is time unit: %d ---------------- " %timer)
		observer.storageReport()

		for s in storages:
			s.callAgents(timer)

		#~ for a in agents:
			#~ a.worked = "NO" # initially, no agents have been working yet

		if timer == sim_time:
			timer = 1
			exit()
			#~ observer.report()

		else:
			timer += 1
			sleep(0.1)
			
			


class Report( OneShotBehaviour ):
	''' Reporting behaviour to be added on the fly at the end of simulation with addBehaviour() '''
	
	def _process( self ):
		''' Print out the stats of all storages '''
		''' TODO: Would be nice to produce some visualization on this '''
		
		with self.myAgent: 
			
			totalInterventions = economyRequests + delayRequests + restoreEconomyRequests + advanceRequests + giveRequests + negotiationRequests

			global Overflow
			for s in storages:
				Overflow += s.ResourceLoss

			say( ".... [ END OF SIMULATION ] ...." )
			say( "******* Number of system interventions: %d" % totalInterventions )
			say( "*********** First intervention happened at time: %d" % firstIntervention )

			say( "******* Number of LT ALERTS: %d" % LTalerts )
			say( "*********** Number of DELAY  requests: %d" % delayRequests )
			say( "*********** Number of ECONOMY requests: %d" % economyRequests )
			say( "*********** Number of NEGOTIATION requests: %d" % negotiationRequests )

			say( "******* Number of UT ALERTS: %d" % UTalerts )
			say( "*********** Number of RESTORE requests: %d" % restoreEconomyRequests )
			say( "*********** Number of ADVANCE requests: %d" % advanceRequests )
			say( "*********** Number of GIVE requests: %d" % giveRequests )
			say( "*********** Overflow of resources: %f" % Overflow )

			for s in storages:
				say( "INDIVIDUAL REPORT FOR STORAGE %s" % s.name )
				say( "- Capacity: %d" % s.maxCapacity )
				say( "- CRL: %d" % s.currentResourceLevel )
				say( "- UT alerts: %d" % s.myUTalerts )
				say( "- Advance reqs: %d" % s.myAdvanceReqs )
				say( "- Resources lost: %f" % s.ResourceLoss )
				say( "- LT alerts: %d" % s.myLTalerts )
				say( "- Economy reqs: %d" % s.myEconomyReqs )
				say( "- Delay reqs: %d" % s.myDelayReqs )
				say( "CRL HISTORY: %s" % s.CRLhistory )
				say( "OVERFLOW per time unit: %s" % s.overflowHistory )



class TalkingAgent( BDIAgent ):
	''' Agent that prints to the console
	Abstract - only to be inherited by other agent classes	
	'''
	def say( self, msg ):
		''' Say something (e.g. print to console for debug purposes) '''
		print '%s: %s' % ( self.name.split( '@' )[ 0 ], str( msg ) )



class Observer:
	''' Observer agent -- collects statistical data about all other agents '''
	
	def storageReport (self):

		for s in storages:

			#~ total_production = s.currentProduction()
			#~ total_consumption = s.currentReqs()

			print("\n Hello, I am STORAGE %s, regularly reporting:" %(s.storageName))
			print(" ---- My resource ID: %d" %s.resourceID)
			print(" ---- My resource level: %f" %s.currentResourceLevel)
			s.CRLhistory.append(s.currentResourceLevel)
			print(" ---- My CRL history: %s" %s.CRLhistory)
			print(" ---- My max capacity: %d" %s.maxCapacity)
			#~ print(" ---- My total production: %f" %total_production)
			#~ print(" ---- My total consumption: %f" %total_consumption)
			print(" ---- My PRODUCERS: %s" %s.myProducers) # ...TO-DO
			print(" ---- My CONSUMERS: %s" %s.myConsumers) # ...TO-DO
			print(" ---- My agents working in economy mode: %s " %s.agentsInEconomy)


	def _setup( self ):
		''' Setup the agent's knowledge base '''
		self.kb = KB()
		self.report = Report()


class Storage:
	
	def __init__ (self, name, crl, maxCapacity, lowerThreshold, upperThreshold, storageCosts, acceptableCost, resourceID, buyerValue, buyerStrategy, sellerValue, sellerStrategy, negTimerMax, worth):

		storages.append(self)

		self.resourceID = resourceID
		self.storageName = name
		self.maxCapacity = maxCapacity
		self.currentResourceLevel = crl
		self.lowerThreshold = lowerThreshold
		self.upperThreshold = upperThreshold
		self.currentOperatingMode = "Normal" #normal, economy, or delayed
		self.agentsByPriority = []
		self.currentlyWorkingAgents = []
		self.NonActiveAgents = []
		self.myAgents = []
		self.myAgentNames = []
		self.myProducers = [] # (names, not class references)
		self.myConsumers = [] # (names, not class references)
		self.myNeighbours = []
		self.agentsInEconomy = []
		self.ResourceLoss = 0
		self.myUTalerts = 0
		self.myLTalerts = 0
		self.myEconomyReqs = 0
		self.myDelayReqs = 0
		self.myAdvanceReqs = 0
		self.CRLhistory = []
		self.overflowHistory = []
		self.storageCosts = storageCosts
		self.acceptableCost = acceptableCost
		self.negotiationAnswer = 0
		
		self.answer = 0

		#NEGOTIATION PARAMETERS:
		self.give = 1
		self.initial = [0,0]

		#self.buyer_initial_offer = [self.need, 1]
		self.seller_initial_offer = [self.give, 10]

		self.buyer_value = buyerValue
		self.buyer_strategy = buyerStrategy

		self.seller_value = sellerValue
		self.seller_strategy = sellerStrategy

		self.negTimer = 0
		self.negTimerMax = negTimerMax

		self.buyer_current_offer = []
		self.seller_current_offer = []

		self.worth = worth


	
class StorageAgent( TalkingAgent, Storage ):
	''' A storage agent in a settlement '''

	class sendingMessageClass (OneShotBehaviour):
		def _process (self):
			pass
			#print "sendingMessageClass of Storage entered"
			

	def sendMessage (self, messageToSend, messageReceiver, messageOntology):		
		msg = ACLMessage()
		msg.setPerformative("inform")
		msg.setOntology(messageOntology)
		#msg.setOntology("testOntology")
		msg.setLanguage( "English" )
		receiver = aid(name="%s@127.0.0.1" %messageReceiver, addresses=["xmpp://%s@127.0.0.1" %messageReceiver])
		msg.addReceiver( receiver )
		msg.setContent( messageToSend )
		self.send( msg )
		print "\n-- Storage %s is now sending message: %s to %s (ontology: %s) -->" %(self.storageName, msg.getContent(), messageReceiver, messageOntology)
		#~ print "-- receiver (full): %s" %receiver
		#~ print "-- ontology: %s" %messageOntology
		

	class receiveMessage(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 20)
			if self.msg:
				print "%s, got a message:" %self.myAgent.storageName
				self.msgContent = self.msg.getContent()
				#print type(self.msgContent)
				print self.msgContent
				
				if "TEST" in self.msgContent:
					print "It's just a freakin' TEST message"
					
				#~ elif isinstance (self.msgContent, int):
					#~ print "I just got a freebie offer: %d" %self.msgContent
					
				else:
					print "SOME OTHER MESSAGE"				
			else:
				print "I waited, but no message for me."
			
			self.myAgent.currentReqs() 

	
	class receiveDelay(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 1)
			
			if self.msg:
				print "\n--> %s has just received DELAY reply from %s:" %(self.myAgent.storageName, self.msg.getSender().getName().partition("@")[0])
				self.msgContent = int(self.msg.getContent())
				print "\n--> %s now calling back its <reqDelay> with parameter: %d" %(self.myAgent.storageName, self.msgContent)
				self.myAgent.reqDelay(self.msgContent)


	class receiveEconomy(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 1)
			
			if self.msg:
				print "\n--> %s has just received ECONOMY reply from %s:" %(self.myAgent.storageName, self.msg.getSender().getName().partition("@")[0])
				self.msgContent = int(self.msg.getContent())
				print "\n--> %s now calling back its <reqEconomy> with parameter: %d" %(self.myAgent.storageName, self.msgContent)
				self.myAgent.reqEconomy(self.msgContent)
		
		
	class negotiationBuying(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 1)
			
			if self.msg:
				print "\n--> %s has just received NEGOTIATION message ariving to ALICE BUYING from %s:" %(self.myAgent.storageName, self.msg.getSender().getName().partition("@")[0])
				self.msgContent = self.msg.getContent()

				offer = list(eval(self.msgContent.partition("[")[2].partition("]")[0]))
				print "%%%%%%%%%%%%%%%%%%%%%%%"
				print "offer is: %s" %offer
				seller = self.msgContent.partition("<")[1] + self.msgContent.partition("<")[2].partition(">")[0] + self.msgContent.partition(">")[1]
				print seller
				print "%%%%%%%%%%%%%%%%%%%%%%%"
				
				#~ offer = list(eval(self.msgContent))
				#~ print offer
				#~ seller = self.msg.getSender().getName()
				#~ seller = self.msg.getSender()
				self.myAgent.buying(offer, seller)
				
	
	class negotiationSelling(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 1)
			
			if self.msg:
				print "\n--> %s has just received NEGOTIATION message from %s:" %(self.myAgent.storageName, self.msg.getSender().getName().partition("@")[0])
				self.msgContent = self.msg.getContent()
				print self.msgContent # THIS IS A FU***** STRING
				# ([79, 1], 2, <StorageAgent(storage1@127.0.0.1, started 139843090052864)>)
				negParam1 = self.msgContent.partition("[")[2].partition("]")[0]
				negParam1 = list(eval(negParam1)) # convert list representation in string to actual list
				negParam2 = int(self.msgContent.partition("]")[2].partition("<")[0].replace(", ", ""))
				negParam3 = self.msgContent.partition("<")[1] + self.msgContent.partition("<")[2].partition(">")[0] + self.msgContent.partition(">")[1]
				initiator = self.msg.getSender().getName()
				#~ print negParam1
				#~ print negParam2
				#~ print negParam3
				#~ print initiator
				self.myAgent.selling(negParam1, negParam2, initiator)
				
				

						
	class receiveFreebies(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 1)
			
			if self.msg:
				print "\n--> %s has just received FREEBIES message from %s:" %(self.myAgent.storageName, self.msg.getSender().getName().partition("@")[0])
				self.msgContent = self.msg.getContent()
				print self.msgContent
				freebie = int(self.msgContent)
				#~ print type(freebie)
				#~ print freebie
				
				if freebie > 0: #incoming give proposal from Alice to Bob
					reply = self.myAgent.acceptResources(freebie)
					print "\n<acceptResources> result in %s: %d, sending reply to: %s" %(self.myAgent.storageName, reply, self.msg.getSender().getName().partition("@")[0])
					self.myAgent.sendMessage(int(reply), self.msg.getSender().getName().partition("@")[0], "freebies")
				
				elif freebie <= 0: #incoming freebie reply from Bob to Alice
					print "%s received acceptance of %d freebies from %s" %(self.myAgent.storageName, (abs(freebie)), self.msg.getSender().getName().partition("@")[0])
					self.myAgent.giveResourcesProcess (abs(freebie))					

					
			else:
				print "I waited, but no message for me."
		

	def __init__(self, name, crl, maxCapacity, lowerThreshold, upperThreshold, storageCosts, acceptableCost, resourceID, buyerValue, buyerStrategy, sellerValue, sellerStrategy, negTimerMax, worth,  *args, **kwargs):
		TalkingAgent.__init__(self, *args, **kwargs)
		Storage.__init__(self, name, crl, maxCapacity, lowerThreshold, upperThreshold, storageCosts, acceptableCost, resourceID, buyerValue, buyerStrategy, sellerValue, sellerStrategy, negTimerMax, worth)
	
	
	def _setup( self ):
		template = ACLTemplate()
		template.setLanguage("English")
		template.setOntology("testOntology")
		t = MessageTemplate(template)
		self.addBehaviour(self.receiveMessage(),t)
		self.addBehaviour(self.sendingMessageClass())
		
		template2 = ACLTemplate()
		template2.setLanguage("English")
		template2.setOntology("freebies")
		t2 = MessageTemplate(template2)
		self.addBehaviour(self.receiveFreebies(),t2)
		
		template3 = ACLTemplate()
		template3.setLanguage("English")
		template3.setOntology("delay")
		t3 = MessageTemplate(template3)
		self.addBehaviour(self.receiveDelay(),t3)
		
		template4 = ACLTemplate()
		template4.setLanguage("English")
		template4.setOntology("economy")
		t4 = MessageTemplate(template4)
		self.addBehaviour(self.receiveEconomy(),t4)
		
		template5 = ACLTemplate()
		template5.setLanguage("English")
		template5.setOntology("buying")
		t5 = MessageTemplate(template5)
		self.addBehaviour(self.negotiationBuying(),t5)
		
		template6 = ACLTemplate()
		template6.setLanguage("English")
		template6.setOntology("selling")
		t6 = MessageTemplate(template6)
		self.addBehaviour(self.negotiationSelling(),t6)
		
		

	def callAgents(self, timer):

		self.myAgents = []
		self.myAgentNames = []
		self.myProducers = []
		self.myConsumers = []

		for key, value in agentStorage.items(): # who are my agents?
			if value == (self):
				self.myAgents.append(key)
				self.myAgentNames.append(key.changerName)

		for a in self.myAgents:
			if a.type == "CONSUMER":
				self.myConsumers.append(a.changerName)
			elif a.type == "PRODUCER":
			  self.myProducers.append(a.changerName)

		for a in self.myAgents:
			a.working(timer)
		
		self.highThresholdAlert()
		self.lowThresholdAlert()
		


	def currentReqs(self): # adds up all the current resource requests of currently ACTIVE agents
		
		#~ print "Entering currentReqs"
		totalReqs = 0

		for c in self.myAgents:
			if timer >= c.workStart and timer <= c.workStop and c.capacity[timer-1] < 0:
				totalReqs = totalReqs + c.capacity[timer-1]
		print "\n * ---- Total active requests at %s: %d\n" %(self.storageName, totalReqs)
		return totalReqs


	def currentProduction(self): # adds up all the current resource productions of currently ACTIVE agents

		totalProduction = 0

		for c in self.myAgents:
			if timer >= c.workStart and timer <= c.workStop and c.capacity[timer-1] > 0:
				totalProduction = totalProduction + c.capacity[timer-1]

		return totalProduction


	def lowThresholdAlert(self):
		
		self.myAgents = [] # identify my agents
		for key, value in agentStorage.items():
			if value == (self):
				self.myAgents.append(key)
		
		if self.currentResourceLevel <= self.lowerThreshold:
			print "\n\n--------------------------------------" + len(self.name)*"-"
			print("----! LOW THRESHOLD ALERT at storage %s! " %self.name )
			print "--------------------------------------" + len(self.name)*"-"
			print(" --- CRL: %f" %self.currentResourceLevel)
			print(" --- LT: %f" %self.lowerThreshold)
			print(" --- Calling agents to delay..\n")

			global LTalerts
			LTalerts += 1

			self.myLTalerts += 1

			global firstIntervention
			if firstIntervention == 0:
				firstIntervention=timer

			self.currentlyWorkingAgents = []

			for agn in self.myAgents: #identifying agents that are currently working
				if timer >= agn.workStart and timer <= agn.workStop and agn.capacity[timer-1] < 0 and agn.worked == "NO": # agn.worked = "NO": the ones which haven't work yet in current time unit
					self.currentlyWorkingAgents.append(agn)

			if len(self.currentlyWorkingAgents) == 0:
				print ("\n NO MORE ACTIVE CONSUMERS TO CALL. \n ")
				return ("nok")

			print("THESE ARE THE CURRENTLY WORKING CONSUMERS: %s" %self.currentlyWorkingAgents)

			self.agentsByPriority = sorted(self.currentlyWorkingAgents, key=operator.attrgetter("priority"))
			print("THESE ARE THE CURRENTLY WORKING, *SORTED* CONSUMERS: %s" %self.agentsByPriority)

			self.reqDelay(0,0)
			# self.reqEconomy(0)
			
			

	def reqDelay(self, reply, *args):

		print "\n\n      <REQUEST DELAY> ACTIVATED by %s\n" %self.storageName

		global delayRequests
		delayRequests += 1
		self.myDelayReqs += 1
		
		answer = reply
		if args:
			i = args[0] 
		else:
			pass
		
		print "\n<answer> value while entering <reqDelay>: %d" %answer
		print "\nPinging index: %d" %i

		totalRequests = abs(self.currentReqs())
		totalProduction = self.currentProduction()
			
		if answer == 0 and i != len(self.agentsByPriority):

			lowConsumer = self.agentsByPriority[i]
			
			#neighbourPing = closestNeighbour.name.partition("@")[0] # extract only name without address
			self.sendMessage(1, lowConsumer.name.partition("@")[0], "delay")
			
			# answer = lowConsumer.delay(lowConsumer, timer+4) # "4" can be later replaced with a variable # ... good times
			i += 1
			sleep(1)
			#~ print "currentResourceLevel1: %f" %self.currentResourceLevel
		
		
		elif answer != 0:
			
			#~ print "entered elif"
			totalRequests = abs(self.currentReqs())
			totalProduction = self.currentProduction()
			self.currentResourceLevel = self.currentResourceLevel - self.agentsByPriority[i-1].capacity[timer-1]
			
			print "Deleting %f consumed by %s from storage %s" %(self.agentsByPriority[i-1].capacity[timer-1], self.agentsByPriority[i-1].name, self.name)
			print "New Resource Level for %s: %f" %(self.name, self.currentResourceLevel)
			print "Total requests currently in %s: %f" %(self.name, totalRequests)
			sleep(0.5)

		friend = i
		
		#~ if (totalProduction + self.currentResourceLevel - totalRequests) > self.lowerThreshold: # mozda je dovoljno da trend bude pozitivan ili neutralan (0), mozda i ne - pratiti simulacije
		print "currentResourceLevel2: %f" %self.currentResourceLevel
		if 	self.currentResourceLevel > self.lowerThreshold:
			print ("\n ** RESOURCE DEFICIT PREVENTED BY DELAYING! ** \n")
			return ("ok")

		elif (self.currentResourceLevel - totalRequests) <= self.lowerThreshold and i == len(self.agentsByPriority):
			print ("\n ** DELAYING FAILED. Calling consumers to economy modes...")
			self.reqEconomy(0,0)

		else:
			print ("\n ** Calling for delays AGAIN... ** ")
			self.reqDelay(0,friend)
	
	
	def reqEconomy(self, reply, *args):

		print "\n\n      <reqEconomy> ENTERED in %s\n" %self.storageName

		global economyRequests
		economyRequests += 1
		self.myEconomyReqs += 1

		if args:
			i = args[0] 
		else:
			pass

		answer = reply

		self.currentlyWorkingAgents = [] # reset the list, because Delay function maybe turned some agents off

		for agn in self.myAgents:
			if timer >= agn.workStart and timer <= agn.workStop and agn.capacity[timer-1] < 0:
				self.currentlyWorkingAgents.append(agn)

		print("THESE ARE THE CURRENTLY WORKING CONSUMERS: %s" %self.currentlyWorkingAgents)
		self.agentsByPriority = sorted(self.currentlyWorkingAgents, key=operator.attrgetter("priority"))
		print("THESE ARE THE CURRENTLY WORKING, *SORTED* CONSUMERS: %s" %self.agentsByPriority)

		if answer == 0 and i != len(self.agentsByPriority):

			lowConsumer = self.agentsByPriority[i]
			print("\n This is the new candidate for economy mode:")
			print (lowConsumer.name)

			#~ answer = lowConsumer.changeMode(lowConsumer) # GOOD times.
			self.sendMessage(1, lowConsumer.name.partition("@")[0], "economy")
			sleep(0.5)

			i+=1

		friend = i # remember who last responded with "ok"; later continue from the next one

		sleep(0.5)
		
		if self.currentResourceLevel > self.lowerThreshold:
			print ("\n ** NICE! Economy mode SAVED the day for the next time unit! ** ")
			return ("ok")

		elif self.currentResourceLevel < self.lowerThreshold and i == len(self.agentsByPriority):
			print ("\n ** Calls for economy mode failed. Time to negotiate with neighbours. ** ")
			self.currentOperatingMode = "economy"

			neededResources = self.lowerThreshold - self.currentResourceLevel + 1

			print (" ** %s asking for neighbour help, needed amount: %f " %(self.name, neededResources))

			negotiationResult = self.startNegotiation(neededResources, 0)

			if negotiationResult == "nn":
				return ("ok")

		else:
			print ("\n ** Calling reqEconomy AGAIN. ** ")
			self.reqEconomy(0,friend) # if there is still not enough resources, but not all consumers were contacted, call the function recursively again


	def Strategy (self, offer, strategy):

		p = offer
		s = strategy

		new_offer = []

		new_quantity = p[0] + s[0]
		new_price = p[1] + p[1]*s[1]
		new_offer = [new_quantity, new_price]
		
		return new_offer



	def Value (self, offer, value):

		p = offer
		k = value
		value_calc = 0

		for i in range(len(p)):
			tmp = p[i]*k[i]
			value_calc += tmp

		return value_calc
		

	
	def selling (self, asked_quantity, timer, buyer):

		print "\n\n      <selling> ENTERED in %s\n" %self.storageName

		buyer_received_offer = asked_quantity
		timer = timer
		buyer = buyer

		print "      timer: %d" %timer

		print("\n\n SELLER %s > The following offer received from Buyer: %s" %(self.name, buyer_received_offer))
		maxQ = self.currentResourceLevel - self.lowerThreshold + 1
		print(" SELLER %s > My CRL: %f" %(self.name, self.currentResourceLevel))
		print(" SELLER %s > Max quantity for spare: %f" %(self.name, maxQ))

		#print (buyer_received_offer)

		if timer >= self.negTimerMax:
			print(" SELLER %s > Time limit exceeded, exciting negotiations now." %(self.name))
			buyer.negTimer = 0
			return 0

		elif timer == 1:
			self.seller_current_offer = self.seller_initial_offer
			print (" SELLER %s > INITIAL OFFER: %s" %(self.name, self.seller_current_offer))
			#print (self.seller_current_offer)

		else:
			new_offer = self.Strategy (self.seller_current_offer, self.seller_strategy)
			self.seller_current_offer = new_offer
			print (" SELLER %s > NEW OFFER: %s" %(self.name, self.seller_current_offer))
			#print (self.seller_current_offer)


		my_value = self.Value (self.seller_current_offer, self.seller_value)
		print(" SELLER %s > My Value: %f" %(self.name, my_value))

		seller_received_value = self.Value (buyer_received_offer, self.seller_value)
		print(" SELLER %s > Received Value: %f" %(self.name, seller_received_value))


		if seller_received_value  >= my_value:
			print ("\n ** SELLER %s > Negotiations Successful by the seller!" %self.name)
			print (" ** SELLER %s > TOTAL ITERATIONS: %d" %(self.name, timer))
			print (" ** SELLER %s > ACCEPTED OFFER: %s" %(self.name, buyer_received_offer))
			buyer.negTimer = 0

			self.worth = self.worth + buyer_received_offer[1]
			buyer.worth = buyer.worth - buyer_received_offer[1]
			self.currentResourceLevel = self.currentResourceLevel - buyer_received_offer[0]
			print (" ** SELLER %s > New Worth Amount: %f" %(self.name, self.worth))
			print (" ** SELLER %s > New CRL: %f" %(self.name, self.currentResourceLevel))
			print (" ** BUYER %s > New Worth Amount: %f" %(buyer.name, buyer.worth))

			answer = buyer_received_offer[0]

			buyer.negotiationAnswer = answer
			return answer

		else:
			print " SELLER %s > CONTACTING THE CLIENT %s WITH OFFER: %s" %(self.name, buyer, self.seller_current_offer)
			#~ seller_answer = buyer.buying (self.seller_current_offer, self) # good. times. 
			message = (self.seller_current_offer, self)
			self.sendMessage(message, buyer.partition("@")[0], "buying")
			
			
			
	def buying (self, counter_offer, seller):

		received_offer = counter_offer
		seller = seller

		print("\n\n       ****** BUYER %s > Iteration number: %d *******" %(self.name, self.negTimer))
		print ("\n")

		if received_offer != self.initial:
			print(" BUYER %s > Received offer from seller: %s" %(self.name, received_offer))

		if self.negTimer >= self.negTimerMax:
			print(" BUYER %s > Time limit exceeded, exciting negotiations now." %self.name)
			self.negTimer = 0

			self.negotiationAnswer = 0
			return 0

		if received_offer == self.initial: # Starting the initial negotiations
			self.need = self.lowerThreshold - self.currentResourceLevel + 1
			seller_max = seller.currentResourceLevel - seller.lowerThreshold - 1
			print(" BUYER %s > I need: %f." %(self.name, self.need))
			print(" BUYER %s > Seller CRL: %f." %(self.name, seller.currentResourceLevel))
			print(" BUYER %s > Seller can give max: %f." %(self.name, seller_max))

			if self.need <= seller_max:
				self.buyer_initial_offer = [self.need, 1]
				self.buyer_current_offer = self.buyer_initial_offer

			else:
				self.buyer_initial_offer = [seller_max, 1]
				self.buyer_current_offer = self.buyer_initial_offer

			print(" BUYER %s > INITIAL OFFER: %s" %(self.name, self.buyer_current_offer))

		else: # continuing the negotiations
			new_offer = self.Strategy (self.buyer_current_offer, self.buyer_strategy)
			self.buyer_current_offer = new_offer

		my_value = self.Value (self.buyer_current_offer, self.buyer_value)
		print(" BUYER %s > My Value: %f" %(self.name, my_value))

		buyer_received_value = self.Value (counter_offer, self.buyer_value)
		print(" BUYER %s > Received Value: %f" %(self.name, buyer_received_value))


		if buyer_received_value  >= my_value:
			print ("\n ** BUYER %s > Negotiations Successful!" %self.name)
			print (" ** BUYER %s > TOTAL ITERATIONS: %d" %(self.name, self.negTimer))
			print (" ** BUYER %s > ACCEPTED OFFER: %s" %(self.name, received_offer))

			self.currentResourceLevel = self.currentResourceLevel + received_offer[0]
			print (" ** BUYER %s > New CRL: %d" %(self.name, self.currentResourceLevel))

			self.negTimer = 0
			self.worth = self.worth - received_offer[1]
			seller.worth = seller.worth + received_offer[1]
			seller.currentResourceLevel = seller.currentResourceLevel - received_offer[0]
			print (" ** BUYER %s > New Worth Amount: %f" %(self.name, self.worth))
			print (" ** SELLER %s > New Worth Amount: %f" %(seller.name, seller.worth))
			print (" ** SELLER %s > New CRL: %f" %(seller.name, seller.currentResourceLevel))

			answer = received_offer[0]

			self.negotiationAnswer = answer
			return answer

		else:
			print "############## NOT SATISFIED ##################"
			self.negTimer += 1 
			print("\n BUYER %s > CONTACTING THE SELLER %s WITH OFFER: %s" %(self.name, seller, self.buyer_current_offer))
			# seller.selling (self.buyer_current_offer, self.negTimer, self) # ... good... times.
			message1 = (self.buyer_current_offer, self.negTimer, self)
			print "sending message %s" %(str(message1))
			#~ print seller.name.partition("@")[0]
			#~ self.sendMessage(message1, seller.name.partition("@")[0], "selling")
			strSeller = str(seller)
			self.sendMessage(message1, strSeller.partition("(")[2].partition("@")[0], "selling")
			sleep(1)

			# SELLER BECOMES STRING IN THE SECOND ITERATION, SO THIS BECOMES A PROBLEM.

	
	def startNegotiation(self, need, j):

		self.negTimer = 0 # ADDED 
		
		global negotiationRequests
		negotiationRequests += 1

		self.myNeighbours = []
		for r in storages:
			if r.resourceID == self.resourceID:
				self.myNeighbours.append(r)

		if not self.myNeighbours:
			print (" * Sorry, no neighbours detected. You are on your own pal.")
			if self.currentResourceLevel <= 0:
				print ("\n\n\n *********** SYSTEM NOT SELF-SUSTAINABLE in time: %d ***********" %timer)
				observer.report()
			return "nn"

		self.myNeighbours.remove(self)

		if not self.myNeighbours:
			print (" * Sorry, no neighbours detected. You are on your own pal.")
			if self.currentResourceLevel <= 0:
				print ("\n\n\n *********** SYSTEM NOT SELF-SUSTAINABLE in time: %d ***********" %timer)
				observer.report()
			return "nn"

		else:
			print (" ** My Neighbours (for negotiation): %s " %self.myNeighbours)

		i = j
		answer = 0
		cost = 0

		if answer == 0 and i != len(self.myNeighbours):
		   closestNeighbour = self.myNeighbours[i]
		   print("\n >> %s pinging neighbour for negotiations: %s" %(self.name, closestNeighbour.name))

		   cost = self.storageCosts.get(closestNeighbour.name)
		   seller_canGive = closestNeighbour.currentResourceLevel - closestNeighbour.lowerThreshold - 1

		   print (" >> Transfer costs from %s: %s" %(closestNeighbour.name, cost))

		   if cost < self.acceptableCost and seller_canGive > 0:
			   print (" >> TRANSFER COST ACCEPTABLE. RESOURCES AVAILABLE. INITIATING NEGOTIATION PROCESS.")

			   self.buying(self.initial, closestNeighbour)
			   answer = self.negotiationAnswer
			   i+=1

		   elif cost < self.acceptableCost and seller_canGive <= 0:
			   print (" >> TRANSFER COST ACCEPTABLE, BUT RESOURCES NOT AVAILABLE.")
			   print (" >> SELLER %s CRL: %f" %(closestNeighbour.name, closestNeighbour.currentResourceLevel))
			   print (" >> SELLER %s LT: %f" %(closestNeighbour.name, closestNeighbour.lowerThreshold))
			   answer = 0
			   i+=1

		   else:
			   print (" >> TRANSFER COST NOT ACCEPTABLE. Moving on.")
			   answer = 0
			   i+=1

		friend = i
		self.currentResourceLevel = self.currentResourceLevel + answer
		totalRequests = self.currentReqs()
		
		sleep(5)

		if self.currentResourceLevel <= 0 and i == len(self.myNeighbours): # if all the neighbours were contacted and there is a lack of resources, NOT SS
			print ("\n\n\n *********** SYSTEM NOT SELF-SUSTAINABLE in time: %d ***********" %timer)
			observer.report()

		elif self.currentResourceLevel > 0 and self.currentResourceLevel < self.lowerThreshold and i != len(self.myNeighbours): # more than 0, less than lower threshold
		  neededResources = self.lowerThreshold - self.currentResourceLevel + 1
		  print ("\n\n ** Calling next neighbour for negotiations ...")
		  self.startNegotiation(neededResources, friend)


		elif self.currentResourceLevel >= self.lowerThreshold: # if above the lower threshold, end negotiations
		  print ("\n * Negotiations successful. Exiting negotiations now.")

		else: # if there are still resources left, less than lower threshold, more than 0, all the neighbours contacted
			print ("\n * Negotiation process insufficient.")
			print (" * %s CRL: %f" %(self.name, self.currentResourceLevel))
			print (" * %s LT: %d" %(self.name, self.lowerThreshold))



	def highThresholdAlert(self):

		self.myAgents = [] # identify my agents
		for key, value in agentStorage.items():
			if value == (self):
				self.myAgents.append(key)

		if self.currentResourceLevel >= self.upperThreshold: # and abs(self.currentReqs()) < self.currentProduction():

			print "\n\n----------------------------------------" + len(self.name)*"-"
			print("----! UPPER THRESHOLD ALERT at storage %s! " %self.name )
			print "----------------------------------------" + len(self.name)*"-"
			print "----- Current resource level: %d" %self.currentResourceLevel
			print "----- High threshold: %d" %self.upperThreshold
			print "----- Calling agents to resume their default capacity.\n"
			global UTalerts
			UTalerts += 1

			self.myUTalerts += 1

			global firstIntervention
			if firstIntervention == 0:
				firstIntervention=timer

			# RESTORING DEFAULT CAPACITY FROM ECONOMY CAPACITY

			j=0

			totalRequests = abs(self.currentReqs())
			totalProduction = self.currentProduction()

			for ag in reversed(self.agentsInEconomy): # reversed saved the day, otherwise not working
				
				if timer >= ag.workStart and timer <= ag.workStop:

					global restoreEconomyRequests
					restoreEconomyRequests += 1
					
					nameString = str(ag) # convert the class instance to string for further manipulation
					consumerName = nameString.partition("(")[2].partition("@")[0] # extract the name of the consumer
					self.sendMessage("RESTORE", consumerName, "testOntology")
					sleep(0.5)
								
					print (" * ---- Agent %s restored to default capacity: %f" %(ag.name, ag.capacity[timer-1]))
					self.agentsInEconomy.remove(ag)
					print (" * ---- Agents left in economy mode: %s" %self.agentsInEconomy)

				else:
					print("Agent %s not currently working." %ag.name)

				if abs(self.currentReqs()) > self.currentProduction():
					print(" * --- Capacity restoration successful. Resources saved by restoration. Exiting now.")
					return
				#else:
					#print(" * Restoration not complete. Calling next agent.")

			print(" -- Capacity restoration complete, but NOT enough. Commencing further mechanisms.")


			self.NonActiveAgents = []

			for agn in self.myAgents: # identify currently non-active consumers in order to activate them prematurely and raise the overall consumption
				if timer < agn.workStart and agn.capacity[timer-1] < 0:
					self.NonActiveAgents.append(agn)

			# GIVE SURPLUS OF RESOURCES TO OTHER STORAGES:

			if len(self.NonActiveAgents) == 0:
				print ("\n NO MORE NON-ACTIVE CONSUMERS TO CALL. \n ")
				#amount = self.currentResourceLevel - self.upperThreshold + self.currentProduction() + self.currentReqs()
				amount = self.currentResourceLevel - self.upperThreshold + 1
				print("\n\n * %s now calling neighbours to GIVE freebies" %self.name)
				print (" * My CRL: %f" %self.currentResourceLevel)
				print (" * My UT value: %f" %self.upperThreshold)
				print (" * MY OFFER: %f" %(amount))

				global giveRequests
				giveRequests += 1

				self.giveResources(amount, 0)

			# REQUEST FOR ADVANCE:

			else:
				print(" * THESE ARE THE CURRENTLY NON-WORKING CONSUMERS: %s" %self.NonActiveAgents)
				self.agentsByPriority = sorted(self.NonActiveAgents, key=operator.attrgetter("priority"))
				print(" * THESE ARE THE CURRENTLY NON-WORKING, *SORTED* CONSUMERS: %s" %self.agentsByPriority)

				self.reqAdvance(0)		
	
	
	def giveResources(self, amount, j):

		print "\n\n      <GIVE RESOURCES> ACTIVATED in %s\n" %self.storageName
		global giveRequests
		giveRequests += 1

		self.myNeighbours = []
		for r in storages:
			if r.resourceID == self.resourceID:
				self.myNeighbours.append(r) # here we have all the neighbours handling the same resource type

		if not self.myNeighbours:
			print (" * Sorry, no neighbours detected. No-one to give freebies :(")
			return "nn"

		self.myNeighbours.remove(self)

		if not self.myNeighbours:
			print (" * Sorry, no neighbours detected. No-one to give freebies :(")
			return "nn"

		else:
			print (" * My Neighbours, sorted by CRL: %s " %self.myNeighbours)
			
		self.amount = amount
		self.j = j
		
		self.giveResourcesProcess(0, self.j, self.amount)


	def giveResourcesProcess (self, answer, *args):

		print "\n\n      <GIVE RESOURCES--PROCESS> ACTIVATED in %s\n" %self.storageName
		if args:
			i = args[0] 
			amount = args[1] 
		else:
			pass
			
		self.answer = answer
		newAmount = 0

		if self.answer == 0 and i != len(self.myNeighbours):
			closestNeighbour = self.myNeighbours[i]
			print(" \n -- Pinging neighbour: %s -->" %closestNeighbour.name)
		   
			i+=1
			neighbourPing = closestNeighbour.name.partition("@")[0] # extract only name without address
			self.sendMessage(amount, neighbourPing, "freebies")
			sleep(1)
		   		   
			# answer = closestNeighbour.acceptResources(amount) # good times. 
			
		friend = i

		self.currentResourceLevel = self.currentResourceLevel - self.answer

		totalRequests = abs(self.currentReqs())
		totalProduction = self.currentProduction()

		sleep(1)
						
		if self.answer == amount:
			print ("\n ** Freebies given away, resources saved.")

		elif self.answer < amount and i != len(self.myNeighbours):
			newAmount = amount - self.answer
			print "newAmount: %d, amount: %d, self.answer: %d" %(newAmount, amount, self.answer)
			print ("\n ** Offering freebies AGAIN, amount to give: %f ** " %newAmount)
			self.giveResourcesProcess(0, friend, newAmount)

		else:
			#currentLoss = amount - answer
			currentLoss = self.currentResourceLevel - self.maxCapacity
			if currentLoss > 0:
				self.ResourceLoss = self.ResourceLoss + currentLoss
				self.currentResourceLevel = self.maxCapacity
				self.overflowHistory.append(currentLoss)
				print ("\n ---- Lost resources just now: %f" %currentLoss)
			#self.currentResourceLevel = self.currentResourceLevel - currentLoss
			print ("\n ---- New Level for %s: %f" %(self.name, self.currentResourceLevel))
			print (" ---- Total resource loss so far for %s: %f" %(self.name, self.ResourceLoss))

	
	
	def acceptResources(self, amount):

		print "\n\n      <ACCEPT RESOURCES> ACTIVATED in %s\n" %self.storageName
		offer = amount
		totalRequests = self.currentReqs()
		totalProduction = self.currentProduction()

		canTake = abs(self.upperThreshold - self.currentResourceLevel - 1)
		print "\n ** %s: ACCEPTING RESOURCES METHOD ENTERED" %self.name
		print (" ** %s: My CRL: %f" %(self.name, self.currentResourceLevel))
		print (" ** %s: My UT value: %f" %(self.name, self.upperThreshold))
		print (" ** %s: My capacity value: %f" %(self.name, self.maxCapacity))
		print (" ** %s: My production: %f" %(self.name, totalProduction))
		print (" ** %s: My consumption: %f" %(self.name, totalRequests))

		if self.currentResourceLevel + totalProduction + totalRequests < self.upperThreshold:
			print (" ** %s: I can take this much: %f" %(self.name, canTake))

			if canTake <= offer:
				self.currentResourceLevel = self.currentResourceLevel + canTake
				print (" ** %s: I took a PARTIAL freeby: %f" %(self.name, canTake))
				print (" ** %s: My new CRL: %f" %(self.name, self.currentResourceLevel))
				return -abs(canTake)
			else:
				self.currentResourceLevel = self.currentResourceLevel + offer
				print (" ** %s: I took a FULL freeby: %f" %(self.name, offer))
				print (" ** %s: My new CRL: %f" %(self.name, self.currentResourceLevel))
				accepting = -abs(offer)
				return accepting

		else:
			print (" * Sorry, don't need it.")
			return 0


class Changer (TalkingAgent):
	''' A consumer or a producer in a settlement (changes resource values in a storage) '''
	
	def __init__ (self, name, priority, capacity, workStart, workStop, belongsTo, eFactor):

		agents.append(self)
		agentStorage.update({self:belongsTo})

		self.changerName = name
		self.priority = priority
		self.capacity = capacity
		self.defaultCapacity = capacity
		self.workStart = workStart
		self.workStop = workStop
		self.originalWorkStart = workStart
		self.originalWorkStop = workStop
		self.mode = "normal"
		self.economyPossible = "YES"
		self.economyFactor = eFactor
		self.advancePossible = "YES"
		self.maxAdvance = 5
		self.delayPossible = "NO"
		self.maxDelay = 6
		self.currentDelay = 0
		self.worked = "NO" # if YES -> this agent has already worked in the current time unit; otherwise NO

		if sum(self.capacity) < 0:
			self.type = "CONSUMER"
		else:
			self.type = "PRODUCER"
	
	


class Consumer( Changer ):
	''' A consumer in a settlement '''
	
	def __init__(self, name, priority, capacity, workStart, workStop, belongsTo, eFactor, *args, **kwargs):
		TalkingAgent.__init__(self, *args, **kwargs)
		Changer.__init__(self, name, priority, capacity, workStart, workStop, belongsTo, eFactor)
		#~ print "new CONSUMER __init__"
	
	
	class receiveMessage(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 2)
			if self.msg:
				print "\nI, %s, got a message from %s:" %(self.myAgent.changerName, self.msg.getSender().getName().partition("@")[0])
				self.msgContent = self.msg.getContent()
				print self.msgContent
				
				if "RESTORE" in self.msgContent:
					self.myAgent.capacity = self.myAgent.defaultCapacity
					print "I have restored my consumption capacity to default values."
				
				else:
					print "SOME OTHER MESSAGE"				
			else:
				print "I waited, but no message for me."
	
	
	class receiveDelayMessage(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 2)
			
			if self.msg:
				print "\n--> I, %s, got a DELAY message from %s:" %(self.myAgent.changerName, self.msg.getSender().getName().partition("@")[0])
				self.msgContent = self.msg.getContent()
				#~ print int(self.msgContent)
				
				delayAnswer = self.myAgent.delay(int(self.msgContent))
				#~ print delayAnswer
				
				if delayAnswer == 0: #incoming give proposal from Alice to Bob
					print ("\n * Sorry, delay not possible for unit: %s." %self.myAgent.name)
					print "\n<delay> result in %s: %d, sending reply to: %s" %(self.myAgent.name, delayAnswer, self.msg.getSender().getName().partition("@")[0])
					self.myAgent.sendMessage(int(delayAnswer), self.msg.getSender().getName().partition("@")[0], "delay")
				
				else:
					print "\n * Ok, delay possible for unit: %s." %self.myAgent.name			
					print "\n<delay> result in %s: %d, sending reply to: %s" %(self.myAgent.name, delayAnswer, self.msg.getSender().getName().partition("@")[0])
					self.myAgent.sendMessage(int(delayAnswer), self.msg.getSender().getName().partition("@")[0], "delay")	
			else:
				print "I waited, but no message for me."	
	
	class receiveEconomyMessage(EventBehaviour):
		def _process(self):
			self.msg = None
			self.msgContent = None
			self.msg = self._receive(True, 2)
			
			if self.msg:
				print "\n--> I, %s, got a ECONOMY message from %s:" %(self.myAgent.changerName, self.msg.getSender().getName().partition("@")[0])
				self.msgContent = self.msg.getContent()
				print int(self.msgContent)
				
				economyAnswer = self.myAgent.changeMode()
				#~ print "\Answer from <changeMode> method: %d" %economyAnswer
				
				if economyAnswer == 0: #incoming give proposal from Alice to Bob
					print ("\n * Sorry, economy not possible for unit: %s." %self.myAgent.name)
					print "\n<changeMode> result in %s: %d, sending reply to: %s" %(self.myAgent.name, economyAnswer, self.msg.getSender().getName().partition("@")[0])
					self.myAgent.sendMessage(int(economyAnswer), self.msg.getSender().getName().partition("@")[0], "economy")
				
				else:
					print "\n * Ok, economy possible for unit: %s." %self.myAgent.name			
					print "\n<changeMode> result in %s: %d, sending reply to: %s" %(self.myAgent.name, economyAnswer, self.msg.getSender().getName().partition("@")[0])
					self.myAgent.sendMessage(int(economyAnswer), self.msg.getSender().getName().partition("@")[0], "economy")	
			else:
				print "I waited, but no message for me."	
						

	def delay (self, delayTime):

		self.currentDelay = delayTime

		if self.delayPossible == "NO" or self.workStart == self.originalWorkStart + self.maxDelay:
			print ("\n * Sorry, delay not possible for unit: %s." %self.name)
			return 0

		elif self.delayPossible == "YES" and (self.workStart + self.currentDelay) <= (self.maxDelay + self.originalWorkStart):
			print ("\n *OK! Operating time delay in FULL effect.")
			print (" * -- OLD WORKTIME OF AGENT %s IS FROM %d TO %d." %(self.name, self.workStart, self.workStop))
			self.workStart = self.workStart + self.currentDelay
			self.workStop = self.workStop + self.currentDelay
			print (" * -- NEW WORKTIME OF AGENT %s IS FROM %d TO %d." %(self.name, self.workStart, self.workStop))
			return self.currentDelay

		elif self.delayPossible == "YES" and (self.workStart + self.currentDelay) > (self.maxDelay + self.originalWorkStart):
			print ("\n *NOT BAD! Operating time delay in PARTIAL effect.")
			print (" * -- OLD WORKTIME OF AGENT %s IS FROM %d TO %d." %(self.name, self.workStart, self.workStop))
			self.workStart = self.workStart + (self.maxDelay + self.originalWorkStart - self.workStart)
			self.workStop = self.workStop + (self.maxDelay + self.originalWorkStop - self.workStop)
			print (" * -- NEW WORKTIME OF AGENT %s IS FROM %d TO %d." %(self.name, self.workStart, self.workStop))
			return self.maxDelay

	
	def changeMode (self): # changing the mode to the ECONOMY mode

		print ("\n FUNCTION: changeMode\n")
		myStorage = agentStorage.get(self)

		if (self.mode == "economy") or (self.economyPossible == "NO"):
			print ("Agent %s already in ECONOMY mode or ECONOMY NOT POSSIBLE." %self.name)
			return 0

		else:
		   print ("\n -- OK! Agent %s now operating in economy mode." %self.name)
		   print(" -- OLD capacity value of the low consumer: %s." %self.capacity[timer-1])
		   self.mode = "economy"
		   myStorage.agentsInEconomy.append(self)
		   self.economyCapacity = self.capacity[:]
		   self.economyCapacity = [self.economyFactor*x for x in self.economyCapacity] # economy mode reduces consumption of resources by (economyFactor) percent
		   self.capacity = self.economyCapacity

		   print(" -- NEW capacity value of the low consumer: %s." %self.capacity[timer-1])
		   print(" -- OLD CRL: %f." %myStorage.currentResourceLevel)
		   difference = abs(self.defaultCapacity[timer-1]) - abs(self.economyCapacity[timer-1])
		   myStorage.currentResourceLevel = myStorage.currentResourceLevel + difference
		   print(" -- NEW CRL: %f." %myStorage.currentResourceLevel)
		   return 1

	class sendingMessageClass(OneShotBehaviour):
		def _process (self):
			pass			

	
	def sendMessage (self, messageToSend, messageReceiver, messageOntology):		
		msg = ACLMessage()
		msg.setPerformative("inform")
		msg.setOntology(messageOntology)
		msg.setLanguage( "English" )
		receiver = aid(name="%s@127.0.0.1" %messageReceiver, addresses=["xmpp://%s@127.0.0.1" %messageReceiver])
		msg.addReceiver(receiver)
		msg.setContent(messageToSend)
		self.send(msg)
		print "\n-- Consumer %s is now sending message: %s to %s (ontology: %s) -->" %(self.name, msg.getContent(), messageReceiver, messageOntology)



	def _setup( self ):
		template = ACLTemplate()
		template.setLanguage("English")
		template.setOntology("testOntology")
		t = MessageTemplate(template)
		self.addBehaviour(self.receiveMessage(),t)
		
		template2 = ACLTemplate()
		template2.setLanguage("English")
		template2.setOntology("delay")
		t2 = MessageTemplate(template2)
		self.addBehaviour(self.receiveDelayMessage(),t2)
		
		template3 = ACLTemplate()
		template3.setLanguage("English")
		template3.setOntology("economy")
		t3 = MessageTemplate(template3)
		self.addBehaviour(self.receiveEconomyMessage(),t3)
		
		self.addBehaviour(self.sendingMessageClass())

		
		
	def working (self,timer):

		myStorage = agentStorage.get(self)
		
		if timer >= self.workStart and timer <= self.workStop:
			worked = "YES"
			print ("\n  > > > %s %s REPORTING \n ------ WORKING FROM %d AND %d" %(self.type, self.changerName, self.workStart, self.workStop))		   
			print (" ------ MY STORAGE: %s" %myStorage.storageName)
			myStorage.currentResourceLevel += self.capacity[timer-1]
			print (" ------ MY CAPACITY: %f" %self.capacity[timer-1])
			print (" ------ NEW RESOURCE LEVEL for %s: %f" %(myStorage.storageName, myStorage.currentResourceLevel))

	


class Producer( Changer ):
	''' A producer in a settlement '''
	
	def __init__(self, name, priority, capacity, workStart, workStop, belongsTo, eFactor, *args, **kwargs):
		TalkingAgent.__init__(self, *args, **kwargs)
		Changer.__init__(self, name, priority, capacity, workStart, workStop, belongsTo, eFactor)
		#print "PRODUCER %s __init__" %self.changerName
		self.sending = None
	
	
	def working (self,timer):

		myStorage = agentStorage.get(self)
		
		if timer >= self.workStart and timer <= self.workStop:
			worked = "YES"
			print ("\n  > > > %s %s REPORTING \n ------ WORKING FROM %d AND %d" %(self.type, self.changerName, self.workStart, self.workStop))		   
			print (" ------ MY STORAGE: %s" %myStorage.storageName)
			myStorage.currentResourceLevel += self.capacity[timer-1]
			print (" ------ MY CAPACITY: %f" %self.capacity[timer-1])
			print (" ------ NEW RESOURCE LEVEL for %s: %f" %(myStorage.storageName, myStorage.currentResourceLevel))


	class sendingMessage(OneShotBehaviour):
		
		def _process(self):
			#print "\n\nEntering sendingMessage _process\n\n"
			msg = ACLMessage()
			msg.setPerformative("inform")
			msg.setLanguage( "English" )
			msg.setOntology("testOntology")
			receiver = aid(name="storage1@127.0.0.1", addresses=["xmpp://storage1@127.0.0.1"])
			msg.addReceiver(receiver)
			msg.setContent("TEST message from producer")
			self.myAgent.send(msg)
			print msg.getContent()

		
	def _setup( self ):
		print "PRODUCER %s enter _setup..." %self.changerName
		#~ template = ACLTemplate()
		#~ template.setSender(aid("Producer1@127.0.0.1",["xmpp://Producer1@127.0.0.1"]))
		#~ t = MessageTemplate(template)
		self.addBehaviour(self.sendingMessage())
		
		#~ sm = sendMessage() # calling these two lines when sending messages from within the agent does not work
		#~ self.addBehaviour(sm, None) #
		
		

observer = Observer()

			

if __name__ == '__main__':
	pass
	#~ talker = TalkingAgent("producer1@127.0.0.1", "secret")
	#~ talker.start()
	
	''' Add simulation configuration here (e.g. number of agents, organizational units, hierarchy'''
	
	########################### SCENARIO 1: ECO-VILLAGE ####################################


	# RESOURCE TRANSFER COSTS (defined by the user):
	storage1Costs = {"UNIT-2" : 1, "UNIT-3" : 2, "UNIT-1-2" : 100}
	storage2Costs = {"UNIT-1" : 1, "UNIT-3" : 1, "UNIT-1-2" : 100}
	storage3Costs = {"UNIT-1" : 2, "UNIT-2" : 1, "UNIT-1-2" : 100}
	storage12Costs = {"UNIT-1" : 100, "UNIT-2" : 100, "UNIT-3" : 100}

	# NEGOTIATIONS PARAMETERS (defined by the user):
	buyerValue = [0.99,-0.01]
	buyerStrategy = [0,0.008]
	sellerValue = [-0.6,0.4]
	sellerStrategy = [1,-0.004]
	negTimerMax = 1000
	worth = 100000

	# ------------------- HOUSE 1

	 # storage parameters: name, crl, maxCapacity, lower threshold, upper threshold, transfer costs, acceptable transfer cost value, resource ID

	storage1 = StorageAgent("UNIT-1", 100, 2000, 300, 1700, storage1Costs, 20, 1, buyerValue, buyerStrategy, sellerValue, sellerStrategy, negTimerMax, worth, 'storage1@127.0.0.1', 'secret')
	storage1.start()

	storage2 = StorageAgent("UNIT-2", 350, 1440, 250, 1100, storage2Costs, 20, 1, buyerValue, buyerStrategy, sellerValue, sellerStrategy, negTimerMax, worth, 'storage2@127.0.0.1', 'secret')
	storage2.start()

	storage3 = StorageAgent("UNIT-3-PV", 680, 1008, 600, 800, storage3Costs, 20, 1, buyerValue, buyerStrategy, sellerValue, sellerStrategy, negTimerMax, worth, 'storage3@127.0.0.1', 'secret')
	storage3.start()

	 # collected rainfall for the September:
	productionDistribution1 = [0,855,0,103.5,85.5,0,13.5,0,0,0,0,0,751.5,1647,292.5,0,0,0,0,1309.5,0,0,0,0,112.5,0,0,562.5,193.5,0,0]
	#~ producer1 = Producer ("producer1@127.0.0.1", "secret", "RAINFALL-U1", 1, productionDistribution1, 1, 30, storages[0], 1)
	producer1 = Producer ("RAINFALL-U1", 1, productionDistribution1, 1, 30, storages[0], 1, "producer1@127.0.0.1", "secret")
	producer1.start()


	 # residents collecting water with 20-liter canisters:
	productionDistribution2 = [0,0,40,0,0,40,60,60,60,60,60,60,0,0,0,60,60,60,60,0,60,40,20,0,60,60,0,60,60,60]
	producer2 = Producer ("HANDWORK-U1", 1, productionDistribution2, 1, 30, storages[0], 1, "producer2@127.0.0.1", "secret")

	 # 50 lit of water per human per day
	consumptionDistribution1 = [-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50,-50]
	cunsumer1 = Consumer ("Person1-U1", 10, consumptionDistribution1, 1, 30, storages[0], 0.5, "consumer1@127.0.0.1", "secret")
	cunsumer1.start()
	
	cunsumer2 = Consumer ("Person2-U1", 10, consumptionDistribution1, 1, 30, storages[0], 0.5, "consumer2@127.0.0.1", "secret")
	cunsumer2.start()
	
	storage1.agentsInEconomy.append(cunsumer1) # for testing purposes only, delete before deployment
	


	startSimulation()
