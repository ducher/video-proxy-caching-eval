# helper functions for simulation purpose

import time

import config


def sleep(delay, transfer=True):
	""" sleep function accelerated according to the speed of simulation """

	speed = config.speed
	if not transfer:
		speed = config.speed*config.wait_acc
	time.sleep(delay/speed)

def sleepsched(delay):
	sleep(delay, False)

def time_(transfer=True):
	""" returns the time according to the simulation.
			if transfer is true, it won't take the the additionnal acceleration
			for the waiting periods into account
	"""
	speed = config.speed
	if not transfer:
		speed = config.speed*config.wait_acc

	return time.monotonic() * speed

base_time = 0
""" can be incremented to skip through time """

def timesched():
	global base_time
	return time_(False) + base_time

def add_time(amount):
	""" skip through time """
	global base_time
	base_time += amount

def real_time(time):
	""" converts simulation time to real time """
	return time * config.speed

def no_active_download(clients):
	""" returns true if no client from the list is currently downloading """
	""" Inefficient way to check if there are still downloads pending """
	for client in clients:
		if client.media_downloading > 0:
			#print("Guilty: "+client.name)
			return False
	return True