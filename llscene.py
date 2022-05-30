#!/usr/bin/python

import json
import lightlogic as ll
import paho.mqtt.client as mqtt
from enum import Enum
import sched, time
from Time import Time
import astral
from astral.sun import sun


class Scene:
	def setPreset(self, preset): pass
	def setLights(self, payload): pass
	def powerON(self): pass
	def powerOFF(self): pass
	def changeTimeMode(self): pass

	class PowerMode(Enum):
		OFF = 0
		ON = 1
		ON_AUTO = 2
		
	def readConfig(self, config):
		self.config = config

		self.temps = self.config['temp_presets']
		self.presets = self.config['presets']
		self.time_modes = self.config['time_modes']

		self.t_manual = self.config['times']['manual']
		self.t_auto = self.config['times']['auto_on']
		self.t_auto_switch = self.config['times']['auto_switch']
		self.motion_off_delay = self.config['times']['motion_off_delay']

		self.mode_change_time = {}
		for mode in self.time_modes:
			self.mode_change_time[mode] = Time(text = self.time_modes[mode]['start_time'])


	def __init__(self, config):
		self.readConfig(config)

		self.main_client = mqtt.Client()
		self.main_client.connect(self.config['mqtt_host'], port=self.config['mqtt_port'])

		self.motion_sensor = ll.SonoffMotion(
			self.config['devices']['motion_sensors']['motion'],
			"Motion Sensor",
			self.main_client
		)

		self.lights = {}
		if 'bulbs' in self.config['devices']:
			for bulb in self.config['devices']['bulbs']:
				self.lights[bulb] = ll.TradfriBulb(
					self.config['devices']['bulbs'][bulb],
					bulb,
					self.main_client
				)

		self.remotes = {}
		self.add_clients = {}
		if 'remote_controls' in self.config['devices']:
			for remote in self.config['devices']['remote_controls']:
				self.add_clients['cli_' + remote] = mqtt.Client()
				self.add_clients['cli_' + remote].connect(self.config['mqtt_host'], port=self.config['mqtt_port'])
				self.remotes[remote] = ll.Styrbar(
					self.config['devices']['remote_controls'][remote],
					remote,
					self.add_clients['cli_' + remote]
				)

		self.city = astral.LocationInfo(
			timezone=self.config['location']['timezone'],
			latitude=self.config['location']['latitude'],
			longitude=self.config['location']['longitude']
		)
		self.scheduler = sched.scheduler(time.time, time.sleep)

		self.power = self.PowerMode.OFF
		self.setLights( {'power': False})
		
		self.detectTimeMode()
		self.next_time_mode = self.curr_time_mode
		self.changeTimeMode()

	# Lights control
	def setLights(self, payload):
		power = None
		brightness = None
		color_temp = None
		color_hex = None
		transition = None

		if 'power' in payload:
			power = payload['power']
		if 'brightness' in payload:
			brightness = payload['brightness']
		if 'color_temp' in payload:
			color_temp = payload['color_temp']
		if 'color_hex' in payload:
			color_hex = payload['color_hex']
		if 'transition' in payload:
			transition = payload['transition']

		for l in self.lights:
			self.lights[l].set(
				power = power,
				brightness = brightness,
				color_temp = color_temp,
				color_hex = color_hex,
				transition = transition
			)

	def move_lights(
		self,
		brightness = None,
		color_temp = None
	):
		for l in self.lights:
			self.lights[l].move(brightness = brightness, color_temp = color_temp)

	# Presets
	def setPreset(self, preset):
		if preset in self.time_modes[self.curr_time_mode]['presets']:
			self.curr_preset = preset
			self.curr_temp = self.presets[self.curr_preset]['temp_preset']
			self.light_all_payload = self.temps[self.curr_temp] | self.presets[self.curr_preset]['settings']
		else:
			raise Exception('preset: "' + preset + '" not found in time_mode "' + self.curr_time_mode + '"')
		

	def nextPreset(self):
		try:
			next_preset = self.time_modes[self.curr_time_mode]['presets'][
				self.time_modes[self.curr_time_mode]['presets'].index(self.curr_preset) + 1
			]
			self.setPreset(next_preset)
			return True
		except IndexError:
			return False 


	def prevPreset(self):
		index = self.time_modes[self.curr_time_mode]['presets'].index(self.curr_preset) - 1
		if index >= 0:
			next_preset = self.time_modes[self.curr_time_mode]['presets'][index]
			self.setPreset(next_preset)
			return True
		else:
			return False 

	# Temp
	def setTemp(self, temp):
		if temp in self.temps:
			self.curr_temp = temp
			self.light_all_payload = self.temps[temp]
		else:
			raise Exception('temp: "' + temp + '" not found in "temp_presets"')
	
	def nextTemp(self):
		try:
			next_temp = list(self.temps.keys() )[
				list(self.temps.keys() ).index(self.curr_temp) + 1
			] 
			self.setTemp(next_temp)
			return True
		except IndexError:
			return False 


	def prevTemp(self):
		index = list(self.temps.keys() ).index(self.curr_temp) - 1
		if index >= 0:
			next_temp = list(self.temps.keys() )[index]
			self.setTemp(next_temp)
			return True
		else:
			return False 

	# Time mode
	def setTimeMode(self, mode):
		if mode in self.time_modes:
			self.curr_time_mode = mode
			self.curr_preset = self.time_modes[self.curr_time_mode]['presets'][0]
			self.setPreset(self.curr_preset)
		else:
			raise Exception('time_mode: "' + mode + '" not found in time_modes"')

	def getSunset(self):
		time = sun(self.city.observer)['sunset']
		print('getSunset: (2:00 +) ' + str(time))
		return Time(time.hour, time.minute, time.second) + Time(2)

	def getSunrise(self):
		time = sun(self.city.observer)['sunrise']
		print('getSunrise: (2:00 +) ' + str(time))
		return Time(time.hour, time.minute, time.second) + Time(2)

	def detectTimeMode(self):
		now = Time().now()
		mode = None
		time = Time()

		for t in self.mode_change_time:
			if now > self.mode_change_time[t]:
				if time <= self.mode_change_time[t]:
					time = self.mode_change_time[t]
					mode = t
		
		if mode is None:
			for t in self.mode_change_time:
				if time <= self.mode_change_time[t]:
					time = self.mode_change_time[t]
					mode = t
		
		self.setTimeMode(mode)

	def getNextTimeMode(self):
		current = self.mode_change_time[self.curr_time_mode]
		mode = None
		time = Time(25)

		for t in self.mode_change_time:
			if current < self.mode_change_time[t]:
				if time > self.mode_change_time[t]:
					time = self.mode_change_time[t]
					mode = t
		
		if mode is None:
			for t in self.mode_change_time:
				if time > self.mode_change_time[t]:
					time = self.mode_change_time[t]
					mode = t
		self.next_time_mode = mode
		return time

	def sceduleOnTime(self, time, func):
		now = Time().now()
		if time <= now:
			time = time + Time(24)
		delay = time - now + Time(0, 1)

		return self.scheduler.enter(float(delay), 1, func)

	def changeTimeMode(self):
		self.setTimeMode(self.next_time_mode)
		time = self.getNextTimeMode()

		if self.time_modes[self.next_time_mode]['astro_args'] is not None:
			if self.time_modes[self.next_time_mode]['astro_args'] == 'sunrise':
				self.mode_change_time[self.next_time_mode] = self.getSunrise()
			elif self.time_modes[self.next_time_mode]['astro_args'] == 'sunset':
				self.mode_change_time[self.next_time_mode] = self.getSunset()
			time = self.mode_change_time[self.next_time_mode]
			print('changeTimeMode: time updated: ' + str(time))
			
		print('changeTimeMode sceduled on: ' + str(time))
		self.sceduleOnTime(time, self.changeTimeMode)

		if self.power != self.PowerMode.OFF:
			if self.time_modes[self.curr_time_mode]['on_time_preset'] is not None:
				if self.time_modes[self.curr_time_mode]['on_time_preset'] == 'off':
					self.setLights( {'power': False, 'transition': self.t_auto_switch})
					self.power = self.PowerMode.OFF
				else:
					self.setPreset(self.time_modes[self.curr_time_mode]['on_time_preset'])
					self.setLights(self.light_all_payload)

	# Misc
	def powerON(self):
		self.setPreset(self.time_modes[self.curr_time_mode]['manual_on_preset'])
		self.setLights({'power': 'True',} | self.light_all_payload)

	def powerOFF(self):
		self.setLights( {'power': False})
		self.power = self.PowerMode.OFF

	def autoON(self):
		pass
	def autoOFF(self):
		pass
	
	# Callbacks
	def callback_motion(self, key):
		if key:
			self.autoON()
		else:
			self.autoOFF()

	def callback_remote(self, key):
		if key == ll.Styrbar.State.UP:
			if self.power == self.PowerMode.OFF:
				self.powerON()
			else:
				if self.nextPreset():
					self.setLights(self.light_all_payload)
			self.power = self.PowerMode.ON

		elif key == ll.Styrbar.State.DOWN:
			if self.power != self.PowerMode.OFF:
				if self.prevPreset():
					self.setLights(self.light_all_payload)
				else:
					self.powerOFF()

		elif key == ll.Styrbar.State.LEFT:
			if self.power == self.PowerMode.OFF:
				self.powerON()
			else:
				if self.nextTemp():
					self.setLights(self.light_all_payload)
			self.power = self.PowerMode.ON

		elif key == ll.Styrbar.State.RIGHT:
			if self.power == self.PowerMode.OFF:
				self.powerON()
			else:
				if self.prevTemp():
					self.setLights(self.light_all_payload)
			self.power = self.PowerMode.ON

		if key == ll.Styrbar.State.UP_HOLD:
			self.move_lights(brightness=30)

		elif key == ll.Styrbar.State.DOWN_HOLD:
			self.move_lights(brightness=-30)

		elif key == ll.Styrbar.State.UP_DOWN_RELEASE:
			self.move_lights(brightness=0)


	def run(self):
		self.motion_sensor.setActionCallback(self.callback_motion)
		for remote in self.remotes:
			self.remotes[remote].setActionCallback(self.callback_remote)

		for client in self.add_clients:
			self.add_clients[client].loop_start()
		self.main_client.loop_start()

		self.scheduler.run()

f = open('config.json')
config = json.load(f)

s = Scene(config)
s.run()