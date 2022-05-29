#!/usr/bin/python

import json
import lightlogic as ll
import paho.mqtt.client as mqtt
from enum import Enum



class Scene:
	def setPreset(self, preset):
		pass
	def setLights(self, payload): pass

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
	
		self.power = self.PowerMode.OFF
		self.curr_time_mode = 'night'

		self.curr_preset = self.time_modes[self.curr_time_mode]['presets'][0]
		self.setPreset(self.curr_preset)
		self.setLights( {'power': False})

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

	# Misc
	def powerON(self):
		self.setPreset(self.curr_preset)
		self.setLights({'power': 'True',} | self.light_all_payload)
		self.power = self.PowerMode.ON

	def powerOFF(self):
		self.setLights( {'power': False})
		self.power = self.PowerMode.OFF

	# Callbacks
	def callback_remote(self, key):

		if key == ll.Styrbar.State.UP:
			if self.power == self.PowerMode.OFF:
				self.powerON()
			else:
				if self.nextPreset():
					self.setLights(self.light_all_payload)

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

		elif key == ll.Styrbar.State.RIGHT:
			if self.power == self.PowerMode.OFF:
				self.powerON()
			else:
				if self.prevTemp():
					self.setLights(self.light_all_payload)

		if key == ll.Styrbar.State.UP_HOLD:
			self.move_lights(brightness=30)

		elif key == ll.Styrbar.State.DOWN_HOLD:
			self.move_lights(brightness=-30)

		elif key == ll.Styrbar.State.UP_DOWN_RELEASE:
			self.move_lights(brightness=0)


	def run(self):
		for remote in self.remotes:
			self.remotes[remote].setActionCallback(self.callback_remote)

		for client in self.add_clients:
			self.add_clients[client].loop_start()
		self.main_client.loop_forever()

f = open('config.json')
config = json.load(f)

s = Scene(config)
s.run()