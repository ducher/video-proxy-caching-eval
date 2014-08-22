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
	speed = config.speed
	if not transfer:
		speed = config.speed*config.wait_acc

	return time.monotonic() * speed

def timesched():
	return time_(False)

def real_time(time):
	""" converts simulation time to real time """
	return time * config.speed