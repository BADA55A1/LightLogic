#!/usr/bin/python

import json
from enum import Enum
import paho.mqtt.client as mqtt


class Device:
	def __init__(self, reference, name = ""):
		self.name = name
		self.reference = reference
	

class Controller(Device):
	def set_action(self, action_callback):
		self.action_callback = action_callback

	def _process_msg(self, msg_struct):
		self.action_callback

	def on_callback(self, client, userdata, message):
		self._process_msg(json.loads(message.payload) )

	def __init__(self, reference, name, mqtt_client):
		Device.__init__(self, reference, name)
		self.action_callback = None
		self.client = mqtt_client
		self.client.subscribe("zigbee2mqtt/" + reference)
		self.client.on_message=self.on_callback
		


class Styrbar(Controller):
	class State(Enum):
		UNDEFINED = 0
		UP = 1
		UP_HOLD = 11
		DOWN = 2
		DOWN_HOLD = 21
		UP_DOWN_RELEASE = 123
		LEFT = 3
		LEFT_HOLD = 31
		LEFT_RELEASE = 32
		RIGHT = 4
		RIGHT_HOLD = 41
		RIGHT_RELEASE = 42
	
	Keys = {
		'':                     State.UNDEFINED,
		'on':                   State.UP,
		'brightness_move_up':   State.UP_HOLD,
		'off':                  State.DOWN,
		'brightness_move_down': State.DOWN_HOLD,
		'brightness_stop':      State.UP_DOWN_RELEASE,
		'arrow_left_click':     State.LEFT,
		'arrow_left_hold':      State.LEFT_HOLD,
		'arrow_left_release':   State.LEFT_RELEASE,
		'arrow_right_click':    State.RIGHT,
		'arrow_right_hold':     State.RIGHT_HOLD,
		'arrow_right_release':  State.RIGHT_RELEASE,
	}

	def __init__(self, reference, name, mqtt_client):
		Controller.__init__(self, reference, name, mqtt_client)
		self.state = self.State.UNDEFINED
	
	def _process_msg(self, msg_struct):
		if 'action' in msg_struct:
			self.state = self.Keys[msg_struct['action']]
		# print(msg_struct)
		print(self.name + ": " + str(self.state) )




mqtt_host = "192.168.1.111"
mqtt_port = 1883
client =mqtt.Client()
client.connect(mqtt_host, port=mqtt_port)

s = Styrbar("0x50325ffffed24be5", "Remote A", client)

client.loop_forever()