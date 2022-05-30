#!/usr/bin/python

import datetime

class Time:
	def __init__(self, hour=None, minute=None, second=None, text=None):
		self.hour = 0
		self.minute = 0
		self.second = 0

		if hour is not None:
			self.hour = hour
		if minute is not None:
			self.minute = minute
		if second is not None:
			self.second = second
		
		if text is not None:
			t_list = text.split(':')

			self.hour = int(t_list[0])
			if len(t_list) > 1:
				self.minute = int(t_list[1])
			if len(t_list) > 2:
				self.second = int(t_list[2])

	def now(self):
		now = datetime.datetime.now()
		return Time(now.hour, now.minute, now.second)
	
	def __float__(self):
		return float(self.hour * 3600 + self.minute * 60 + self.second)

	def __str__(self):
		return str(self.hour) + ':' + str(self.minute) + ':' + str(self.second)

	def __add__(self, other):
		hour = self.hour + other.hour
		minute = self.minute + other.minute
		second = self.second + other.second
		return Time(hour, minute, second)

	def __sub__(self, other):
		hour = self.hour - other.hour
		minute = self.minute - other.minute
		second = self.second - other.second
		return Time(hour, minute, second)

	def __lt__(self, other):
		if self.hour == other.hour:
			if self.minute == other.minute:
				if self.second == other.second:
					return False
				else:
					return self.second < other.second
			else:
				return self.minute < other.minute
		else:
			return self.hour < other.hour

	def __le__(self, other):
		if self.hour == other.hour:
			if self.minute == other.minute:
				if self.second == other.second:
					return True
				else:
					return self.second < other.second
			else:
				return self.minute < other.minute
		else:
			return self.hour < other.hour
		

	def __gt__(self, other):
		if self.hour == other.hour:
			if self.minute == other.minute:
				if self.second == other.second:
					return False
				else:
					return self.second > other.second
			else:
				return self.minute > other.minute
		else:
			return self.hour > other.hour
		

	def __ge__(self, other):
		if self.hour == other.hour:
			if self.minute == other.minute:
				if self.second == other.second:
					return True
				else:
					return self.second > other.second
			else:
				return self.minute > other.minute
		else:
			return self.hour > other.hour
		