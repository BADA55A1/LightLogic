#!/usr/bin/python

import sched, time
from enum import Enum
import paho.mqtt.client as mqtt
import lightlogic as ll


mqtt_host = "192.168.1.111"
mqtt_port = 1883

time_day2cold = '19:00' 
time_cold2neutral = '20:00'
time_neutral2warm = '22:00'
time_warm2night = '00:00'
time_night2day = '07:00'

bulb_list = {
	'desk_a': '0x04cd15fffebf6cd8',
	'desk_b': '0x50325ffffeea697c',
	'bed':    '0x04cd15fffe6bd611',
	'stairs': '0x2c1165fffea8a954'
}

addr_remote_a = '0x50325ffffed24be5'
addr_motion_sensor = '0x00124b0025092707'

class TimeMode(Enum):
	DAY = 0
	EVENING_COLD = 1
	EVENING_NEUTRAL = 2
	EVENING_WARM = 3
	NIGHT = 4

class LocationMode(Enum):
	ALL = 0
	STAIRS = 1
	STAIRS_DESK = 2
	DESK = 3
	BED = 4

class MotionMode(Enum):
	IDDLE = 0
	ACTIVE = 1
	LONG_ACTIVE = 2

class LogicMode(Enum):
	AUTO = 0
	MANUAL = 1

class PowerMode(Enum):
	OFF = 0
	ON_AUTO = 1
	ON_MANUAL = 2

# class Mode:
# 	def __init__(self, brightness):


# Init MQTT
client =mqtt.Client()
client.connect(mqtt_host, port=mqtt_port)

client_a =mqtt.Client()
client_a.connect(mqtt_host, port=mqtt_port)

# Connecting
remote_a = ll.Styrbar(addr_remote_a, "Remote A", client)
motion_sensor = ll.SonoffMotion(addr_motion_sensor, "Motion Sensor", client_a)

lamp = {}
for bulb in bulb_list:
	lamp[bulb] = ll.TradfriBulb(bulb_list[bulb], bulb, client)

[print(l) for l in lamp]

mode_time = TimeMode.DAY
mode_location = LocationMode.ALL
mode_motion = MotionMode.IDDLE
mode_logic = LogicMode.AUTO
mode_power = PowerMode.OFF


def set_lights(
	power = None,
	brightness = None,
	color_temp = None
):
	for l in lamp:
		print(l)
		lamp[l].set(power=power, brightness=brightness, color_temp=color_temp, transition=2)

def move_lights(
	brightness = None,
	color_temp = None
):
	for l in lamp:
		print(l)
		lamp[l].move(brightness = brightness, color_temp = color_temp)

color_temp = [
	ll.TradfriBulb.TEMPERATURE_COLD,
	(ll.TradfriBulb.TEMPERATURE_COLD + ll.TradfriBulb.TEMPERATURE_NEUTRAL) / 2,
	ll.TradfriBulb.TEMPERATURE_NEUTRAL,
	(ll.TradfriBulb.TEMPERATURE_WARM + ll.TradfriBulb.TEMPERATURE_NEUTRAL) / 2,
	ll.TradfriBulb.TEMPERATURE_WARM
]

c_temp_p = 0

s = sched.scheduler(time.time, time.sleep)
s_event = None

def remote_callback(var):
	print(var)
	global c_temp_p, color_temp, mode_power, s, s_event
	match var:
		case ll.Styrbar.State.UP:
			set_lights(power=True)
			if s_event is not None:
				s.cancel(s_event)
			mode_power = PowerMode.ON_MANUAL

		case ll.Styrbar.State.DOWN:
			set_lights(power=False)
			if s_event is not None:
				s.cancel(s_event)
			mode_power = PowerMode.OFF

		case ll.Styrbar.State.LEFT:
			if c_temp_p > 0:
				c_temp_p -= 1
				set_lights(color_temp = int(color_temp[c_temp_p]) )

		case ll.Styrbar.State.RIGHT:
			if c_temp_p < 4:
				c_temp_p += 1
				set_lights(color_temp = int(color_temp[c_temp_p]) )

		case ll.Styrbar.State.UP_HOLD:
			move_lights(brightness=20)

		case ll.Styrbar.State.DOWN_HOLD:
			move_lights(brightness=-20)

		case ll.Styrbar.State.UP_DOWN_RELEASE:
			move_lights(brightness=0)

def disable_lights():
	set_lights(power=False)
	mode_power = PowerMode.OFF

def motion_callback(var):
	global mode_power, s, s_event
	if mode_power is not PowerMode.ON_MANUAL:
		if(var):
			set_lights(power=True, brightness=180)
			mode_power = PowerMode.ON_AUTO
		else:
			if s_event is not None:
				s.cancel(s_event)
			s_event = s.enter(5*60, 1, disable_lights)
			s.run()

	

remote_a.setActionCallback(remote_callback)
motion_sensor.setActionCallback(motion_callback)

client.loop_start()
client_a.loop_forever()
# client.loop_forever()