import urllib
import urllib2
import json
import sys
import httplib
import logging
import re
import xml.dom.minidom, xml.sax.saxutils
import splunk.entity as entity
from socket import timeout
from datetime import datetime



#set up logging suitable for splunkd comsumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)
config = {}

# Set the datetime globally to make sure all outputs have the same timestamp
dateTimeNow = str(datetime.now())

# These are the GUI Options
SCHEME = """<scheme>
	<title>Nest - Nest.com Thermostat Information</title>
	<description>Collect usage data from your Nest thermostat by pulling data from Nest.com's webapp.</description>
	<use_external_validation>true</use_external_validation>
	<streaming_mode>simple</streaming_mode>
	<endpoint>
		<args>
			<arg name="username">
				<title>Nest Account</title>
				<description>The account you use to log into Nest.com with.</description>
			</arg>
			<arg name="password">
				<title>Password</title>
				<description>The associated password for your Nest.com account.</description>
			</arg>
		</args>
	</endpoint>
</scheme>
"""

class Nest:
	def __init__(self, username, password):
		self.username = username
		self.password = password
		self.devices = []
		self.structures = []

	def loads(self, res):
			if hasattr(json, "loads"):
				res = json.loads(res)
			else:
				res = json.read(res)
			return res

	def do_subscribe(self, data):
		req = urllib2.Request(
				self.transport_url + "/v5/subscribe",
				json.dumps(data),
				headers = {
					"user-agent": "Nest/1.1.0.10 CFNetwork/548.0.4",
					"Authorization": "Basic " + self.access_token,
					"X-nl-user-id": self.userid,
					"X-nl-subscribe-timeout": "10",
					"X-nl-protocol-version": "1",
					"Connection": "close"
				}
			)

		res = urllib2.urlopen(req, timeout = 5).read()
		res = self.loads(res)
		return res


	def login(self):
		data = urllib.urlencode({"username": self.username, "password": self.password})

		req = urllib2.Request(
				"https://home.nest.com/user/login",
				data,
				{"user-agent":"Nest/1.1.0.10 CFNetwork/548.0.4"}
			)

		res = urllib2.urlopen(req).read()

		res = self.loads(res)

		self.transport_url = res["urls"]["transport_url"]
		self.weather_url = res["urls"]["weather_url"]
		self.access_token = res["access_token"]
		self.userid = res["userid"]

		#print json.dumps(res)

	def get_weather(self, zip):
		req = urllib2.Request(
					self.weather_url + zip,
					headers = {
						"user-agent": "Nest/1.1.0.10 CFNetwork/548.0.4",
						"Authorization": "Basic " + self.access_token,
						"X-nl-user-id": self.userid,
						"X-nl-subscribe-timeout": "10",
						"X-nl-protocol-version": "1",
						"Connection": "close"
					}
				)

		res = urllib2.urlopen(req, timeout = 5).read()
		res = self.loads(res)

		for zipcode in res:
			zipcodeData = res[zipcode]

			# We don't need/want the forecast
			zipcodeData.pop("forecast", None)
			zipcodeData["Time"] = dateTimeNow
			zipcodeData["Collection"] = "weather"			

			print json.dumps(zipcodeData, sort_keys = True)

		return res


	def get_structures(self):

		if self.structures:
			return self.structures

		def clean_struct_name(struct):
			return struct.replace("structure.","")

		userObjectKey = {
			"objects": [{
				"object_key": "user.%s" % (self.userid)
			}]
		}		
		res = self.do_subscribe(userObjectKey)
		self.structures = res["objects"][0]["value"]["structures"]
		self.structures = map(clean_struct_name, self.structures)

		return self.structures

	def get_devices(self):

		if self.devices:
			return self.devices

		def clean_device_name(device):
			return device.replace("device.","")

		for struct in self.get_structures():
			structureObjectKey = {
				"objects": [{
					"object_key": "structure.%s" % struct
				}]
			}				

			res = self.do_subscribe(structureObjectKey)
			devices = res["objects"][0]["value"]["devices"]
			devices = map(clean_device_name,devices)
			self.devices += devices

		return self.devices

	def get_device_object_key(self, device, object_key):
		objectData = 	{
			"objects": [{
				"object_key": "%s.%s" % (object_key, device)
			}]
		}	
		res = self.do_subscribe(objectData)
		res = res["objects"][0]["value"]

		# Append some output information
		res["Time"] = dateTimeNow
		res["Collection"] = object_key

		# Special case for printing structure data
		if object_key == "structure":
			res["Structure"] = device
			# Also print out weather info for structures
			self.get_weather(res["postal_code"])
		else:
			res["Device"] = device

		res["object_key"] = "%s.%s" % (object_key, device)

		print json.dumps(res, sort_keys = True)


def run():		
	config = get_config()

	# config = {
	# 	"username": "rich@ricapar.net",
	# 	"password": "kingdusty"
	# }

	try:
		n = Nest(config["username"], config["password"])
		n.login()
	except Exception,e:
		errorOut = {
			"Time": dateTimeNow,
			"Collection": "error",
			"error": "An error occured while trying to log into Nest.com",
			"error_raw": str(e)
		}
		print json.dumps(errorOut, sort_keys = True)		
		sys.exit(1)

	objectKeysByDevice = [
		"schedule",
		"link",
		"device",
		"shared",
		"energy_latest"
	]

	try:

		devices = n.get_devices()
		structures = n.get_structures()

		# Weather is also printed for structures!
		for struct in structures:
			n.get_device_object_key(struct, "structure")

		#sys.exit(0)

		for device in devices:
			for key in objectKeysByDevice:
				n.get_device_object_key(device, key)


	except Exception,e:
		errorOut = {
			"Time": dateTimeNow,
			"Collection": "error",
			"error": "An exception was caught while trying to connect to Nest.com:",
			"error_raw": str(e)
		}
		print json.dumps(errorOut, sort_keys = True)		
		sys.exit(1)



# Everything from here below is boilerplate code!


def do_scheme():
	print SCHEME

def print_error(s):
	print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)


def get_config():
	try:
		# read everything from stdin
		config_str = sys.stdin.read()

		# parse the config XML
		doc = xml.dom.minidom.parseString(config_str)
		root = doc.documentElement
		conf_node = root.getElementsByTagName("configuration")[0]
		if conf_node:
			logging.debug("XML: found configuration")
			stanza = conf_node.getElementsByTagName("stanza")[0]
			if stanza:
				stanza_name = stanza.getAttribute("name")
				if stanza_name:
					logging.debug("XML: found stanza " + stanza_name)
					config["name"] = stanza_name
					params = stanza.getElementsByTagName("param")
					for param in params:
						param_name = param.getAttribute("name")
						logging.debug("XML: found param '%s'" % param_name)
						if param_name and param.firstChild and \
							param.firstChild.nodeType == param.firstChild.TEXT_NODE:
							data = param.firstChild.data
							config[param_name] = data
							logging.debug("XML: '%s' -> '%s'" % (param_name, data))

		checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
		if checkpnt_node and checkpnt_node.firstChild and \
			checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
			config["checkpoint_dir"] = checkpnt_node.firstChild.data

		if not config:
			raise Exception, "Invalid configuration received from Splunk."

		# just some validation: make sure these keys are present (required)
		validate_conf(config, "username")
		validate_conf(config, "password")

	except Exception, e:
		raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

	return config

def validate_conf(config, key):
    if key not in config:
        raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key

def get_validation_data():
	val_data = {}

	# read everything from stdin
	val_str = sys.stdin.read()

	# parse the validation XML
	doc = xml.dom.minidom.parseString(val_str)
	root = doc.documentElement

	logging.debug("XML: found items")
	item_node = root.getElementsByTagName("item")[0]
	if item_node:
		logging.debug("XML: found item")

		name = item_node.getAttribute("name")
		val_data["stanza"] = name

		params_node = item_node.getElementsByTagName("param")
		for param in params_node:
			name = param.getAttribute("name")
			logging.debug("Found param %s" % name)
			if name and param.firstChild and \
			   param.firstChild.nodeType == param.firstChild.TEXT_NODE:
				val_data[name] = param.firstChild.data

	return val_data



if __name__ == '__main__':
	if len(sys.argv) > 1:
		if sys.argv[1] == "--scheme":
			do_scheme()
		elif sys.argv[1] == "--validate-arguments":
			if len(sys.argv) > 4:
				validate_config(sys.argv[2],sys.argv[3],sys.argv[4])
			else:
				print 'supply username and password'
		elif sys.argv[1] == "--test":
			print 'No tests for the scheme present'
		else:
			print 'You giveth weird arguments'
	else:
		run()

	sys.exit(0)


