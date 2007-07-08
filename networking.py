## THE NETWORKING CLASS
## WRITTEN DECEMBER 18TH, 2006
## RELEASED UNDER THE GNU General Public License

## WRITTEN IN PYTHON, CAN NOT BE USED ALONE
## MUST BE IMPORTED VIA import networking
## TO ANOTHER PROJECT IF YOU WISH TO USE IT

import os,sys
if __name__ == '__main__':
	os.chdir(os.path.dirname(os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))))

#import the library of random functions that we need here
#this is also written by me, for this purpose
import misc
#import some other random libraries that we're gonna need
import re,sys,threading,thread

#much thanks to wieman01 for help and support with various types of encyption
#also thanks to foxy123, yopnono, and the many others who reported bugs helped
#and helped keep this project moving

class Wireless:

	wireless_interface = None
	wired_interface = None
	wpa_driver = None
	ConnectingThread = None

	#Create a function to scan for wireless networks
	def Scan(self,essid=None):

		#we ask for an essid, because then we can see hidden networks

		#####
		## DECLARE THE REGEX PATTERNS
		#####

		#init the regex patterns that will be used to search the output of iwlist scan for info
		#these are well tested, should work on most cards
		essid_pattern		= re.compile('.*ESSID:"(.*?)"\n',re.DOTALL | re.I | re.M  | re.S)
		ap_mac_pattern		= re.compile('.*Address: (.*?)\n',re.DOTALL | re.I | re.M  | re.S)
		channel_pattern		= re.compile('.*Channel:? ?(\d\d?)',re.DOTALL | re.I | re.M  | re.S)
		strength_pattern	= re.compile('.*Quality:?=? ?(\d\d*)',re.DOTALL | re.I | re.M  | re.S)
		mode_pattern		= re.compile('.*Mode:(.*?)\n',re.DOTALL | re.I | re.M  | re.S)

		wep_pattern		= re.compile('.*Encryption key:(.*?)\n',re.DOTALL | re.I | re.M  | re.S)
		wpa1_pattern		= re.compile('(WPA Version 1)',re.DOTALL | re.I | re.M  | re.S)
		wpa2_pattern 		= re.compile('(WPA2)',re.DOTALL | re.I | re.M  | re.S)

		#####
		## PREPARE THE INTERFACE
		#####

		#prepare the interface for scanning
		#note that this must be run as root, otherwise we're gonna have trouble
		misc.Run('ifconfig ' + self.wireless_interface + ' up')

		essid = misc.Noneify(essid)
		if not essid == None:
			#if there is a hidden essid, we need to tell the computer what it is
			#then when it is scanned it will be recognized
			print "setting hidden essid..." + essid
			misc.Run('iwconfig ' + self.wireless_interface + ' essid "' + essid + '"')

		#####
		## RUN THE SCAN
		#####

		#run iwlist scan and get the avaliable networks
		#save them to scan_data - all in one big string
		scandata = misc.Run('iwlist ' + self.wireless_interface + ' scan')

		#####
		## PROCESS THE DATA
		#####

		#split the networks apart, using Cell as our split point
		#this way we can look at only one network at a time
		networks = scandata.split( '   Cell ' )

		#declare
		i=0
		#make an array for the aps
		aps = {}
		for cell in networks:
			#search to see if there is an essid in this section
			#if there isn't, that means that it is useless
			#so we don't use it then

			#set essid to the value, this is just a temp variable
			if cell.count("ESSID:") > 0:
				#since an essid was found,
				#we will extract the rest of the info
				#make a dictionary for the data
				CurrentNetwork = {}

				#use the RunRegex function to neaten up our code
				#all it does for us is run the regex on the string
				#and return the result
				#but it makes this code look pretty

				CurrentNetwork["essid"] = misc.RunRegex(essid_pattern,cell)

				if CurrentNetwork["essid"] == "<hidden>":
					CurrentNetwork["hidden"] = True
					#change the name so it doesn't screw stuff up
					#because it looks like HTML - GTK no like
					CurrentNetwork["essid"] = "Hidden"
				else:
					CurrentNetwork["hidden"] = False

				CurrentNetwork["channel"] = misc.RunRegex(channel_pattern,cell)
				CurrentNetwork["bssid"] = misc.RunRegex(ap_mac_pattern,cell)
				print "	##### " + CurrentNetwork["bssid"]
				CurrentNetwork["mode"] = misc.RunRegex(mode_pattern,cell)

				#since encryption needs a True or False
				#we have to do a simple if then to set it
				if misc.RunRegex(wep_pattern,cell) == "on":
					CurrentNetwork["encryption"] = True
					#set this, because if it is something else this will be overwritten
					CurrentNetwork["encryption_method"] = "WEP"

					if misc.RunRegex(wpa1_pattern,cell) == "WPA Version 1":
						CurrentNetwork["encryption_method"] = "WPA"

					if misc.RunRegex(wpa2_pattern,cell) == "WPA2":
						CurrentNetwork["encryption_method"] = "WPA2"
				else:
					CurrentNetwork["encryption"] = False
				#end If

				#since stength needs a -1 if the quality isn't found
				#we need a simple if then to set it
				if misc.RunRegex(strength_pattern,cell):
					CurrentNetwork["quality"] = misc.RunRegex(strength_pattern,cell)
				else:
					CurrentNetwork["quality"] = -1
				#end If

				#add this network to the list of networks
				aps[ i ] = CurrentNetwork
				#now increment the counter
				i+=1
		#end For

		#run a bubble sort
		#to list networks by signal strength
		going = True

		while going:
			sorted = False
			for i in aps:
				#set x to the current number
				x = int(i)
				#set y to the next number
				y = int(i+1)

				#only run this if we actually have another element after the current one
				if (len(aps) > i+1):

					#move around depending on qualities
					#we want the lower qualities at the bottom of the list
					#so we check to see if the quality below the current one
					#is higher the current one
					#if it is, we swap them

					if (int(aps[int(y)]["quality"]) > int(aps[int(x)]["quality"])):
						#set sorted to true so we don't exit
						sorted=True
						#do the move
						temp=aps[y]
						aps[y]=aps[x]
						aps[x]=temp
					#end If
				#end If
			#end For

			if (sorted == False):
				going = False
			#end If
		#end While

		#return the list of sorted access points
		return aps

	#end Function Scan

	def Connect(self,network):
		#call the thread, so we don't hang up the entire works
		self.ConnectingThread = self.ConnectThread(network,self.wireless_interface,self.wired_interface,self.wpa_driver)
		self.ConnectingThread.start()
		return True

	class ConnectThread(threading.Thread):
		IsConnecting = None
		ConnectingMessage = None
		ShouldDie = False
		lock = thread.allocate_lock()

		def __init__(self,network,wireless,wired,wpa_driver):
			threading.Thread.__init__(self)
			self.network = network
			self.wireless_interface = wireless
			self.wired_interface = wired
			self.wpa_driver = wpa_driver
			self.IsConnecting = False
			self.lock.acquire()
			self.ConnectingMessage = 'interface_down'
			self.lock.release()
			#lock = thread.allocate_lock()

		def GetStatus(self):
			print "status request"
			print "acqlock",self.lock.acquire()
			print "	...lock acquired..."
			message = self.ConnectingMessage
			#return "bob" #self.ConnectingMessage
			self.lock.release()
			print "	...lock released..."
			return message

		def run(self):
			#note that we don't put the wired interface down
			#but we do flush all wired entries from the routing table
			#so it shouldn't be used at all.

			self.IsConnecting = True
			network = self.network
			
			#put it down
			print "interface down..."
			self.lock.acquire()
			self.ConnectingMessage = 'interface_down'
			self.lock.release()
			misc.Run("ifconfig " + self.wireless_interface + " down")

			#set a false ip so that when we set the real one, the correct
			#routing entry is created
			print "Setting false ip..."
			self.lock.acquire()
			self.ConnectingMessage = 'resetting_ip_address'
			self.lock.release()

			misc.Run("ifconfig " + self.wired_interface + " 0.0.0.0")
			misc.Run("ifconfig " + self.wireless_interface + " 0.0.0.0")

			#bring it up
			print "interface up..."
			self.lock.acquire()
			self.ConnectingMessage = 'interface_up'
			self.lock.release()

			print misc.Run("ifconfig " + self.wireless_interface + " up")

			print "killing wpa_supplicant, dhclient, dhclient3"
			self.lock.acquire()
			self.ConnectingMessage = 'removing_old_connection'
			self.lock.release()

			misc.Run("killall dhclient dhclient3 wpa_supplicant")

			#check to see if we need to generate a PSK

			if not network.get('key')== None:
				self.lock.acquire()
				self.ConnectingMessage = 'generating_psk'
				self.lock.release()

				print "generating psk..."
				key_pattern = re.compile('network={.*?\spsk=(.*?)\n}.*',re.DOTALL | re.I | re.M  | re.S)
				network["psk"] = misc.RunRegex(key_pattern,misc.Run('wpa_passphrase "' + network["essid"] + '" "' + network["key"] + '"'))
			#generate the wpa_supplicant file...
			if not network.get('enctype') == None:
				self.lock.acquire()
				self.ConnectingMessage = 'generating_wpa_config'
				self.lock.release()

				print "generating wpa_supplicant configuration file..."
				misc.ParseEncryption(network)
				print "wpa_supplicant -B -i " + self.wireless_interface + " -c \"encryption/configurations/" + network["bssid"].replace(":","").lower() + "\" -D " + self.wpa_driver
				misc.Run("wpa_supplicant -B -i " + self.wireless_interface + " -c \"encryption/configurations/" + network["bssid"].replace(":","").lower() + "\" -D " + self.wpa_driver)

			print "flushing the routing table..."
			self.lock.acquire()

			self.ConnectingMessage = 'flushing_routing_table'
			self.lock.release()

			misc.Run("ip route flush dev " + self.wireless_interface)
			misc.Run("ip route flush dev " + self.wired_interface)

			print "configuring the wireless interface..."
			self.lock.acquire()

			self.ConnectingMessage = 'configuring_interface'
			self.lock.release()

			if network["mode"].lower() == "master":
				misc.Run("iwconfig " + self.wireless_interface + " mode managed")
			else:
				misc.Run("iwconfig " + self.wireless_interface + " mode " + network["mode"])

			misc.Run("iwconfig " + self.wireless_interface + " essid \"" + network["essid"] + "\" channel " + str(network["channel"])) + " ap " + network["bssid"]

			if not network.get('broadcast') == None:
				self.lock.acquire()

				self.ConnectingMessage = 'setting_broadcast_address'
				self.lock.release()

				print "setting the broadcast address..." + network["broadcast"]
				misc.Run("ifconfig " + self.wireless_interface + " broadcast " + network["broadcast"])


			if not network.get("dns1") == None:
				self.lock.acquire()
				self.ConnectingMessage = 'setting_static_dns'
				self.lock.release()
				print "setting the first dns server...", network["dns1"]
				resolv = open("/etc/resolv.conf","w")
				misc.WriteLine(resolv,"nameserver " + network["dns1"])
				if not network.get("dns2") == None:
					print "setting the second dns server...", network["dns2"]
					misc.WriteLine(resolv,"nameserver " + network["dns2"])
				if not network.get("dns3") == None:
					print "setting the third dns server..."
					misc.WriteLine(resolv,"nameserver " + network["dns3"]))

			if not network.get('ip') == None:
				self.lock.acquire()

				self.ConnectingMessage = 'setting_static_ip'
				self.lock.release()

				print "setting static ips..."
				misc.Run("ifconfig " + self.wireless_interface + " " + network["ip"] )
				misc.Run("ifconfig " + self.wireless_interface + " netmask " + network["netmask"] )
				print "adding default gateway..." + network["gateway"]
				misc.Run("route add default gw " + network["gateway"])
			else:
				#run dhcp...
				self.lock.acquire()

				self.ConnectingMessage = 'running_dhcp'
				self.lock.release()

				print "running dhcp..."
				if not self.ShouldDie:
					misc.Run("dhclient " + self.wireless_interface)

			self.lock.acquire()
			self.ConnectingMessage = 'done'
			self.lock.release()

			print "done"
			self.IsConnecting = False



		#end function Connect
	#end class Connect

	def GetSignalStrength(self):
		output = misc.Run("iwconfig " + self.wireless_interface)
		strength_pattern	= re.compile('.*Quality:?=? ?(\d+)',re.DOTALL | re.I | re.M  | re.S)
		return misc.RunRegex(strength_pattern,output)
	#end function GetSignalStrength

	def GetCurrentNetwork(self):
		output = misc.Run("iwconfig " + self.wireless_interface)
		essid_pattern	= re.compile('.*ESSID:"(.*?)"',re.DOTALL | re.I | re.M  | re.S)
		return misc.RunRegex(essid_pattern,output)
	#end function GetCurrentNetwork

	def GetIP(self):
		output = misc.Run("ifconfig " + self.wireless_interface)
		ip_pattern	= re.compile(r'inet [Aa]d?dr[^.]*:([^.]*\.[^.]*\.[^.]*\.[0-9]*)',re.S)
		return misc.RunRegex(ip_pattern,output)
	#end function GetIP

	def CreateAdHocNetwork(self,essid,channel,ip,enctype,key,encused,ics):
		misc.Run("killall dhclient dhclient3 wpa_supplicant") #remove wpa_supplicant, as it can cause the connection to revert to
		#previous networks...
		misc.Run('ifconfig ' + self.wireless_interface + ' down')
		misc.Run('iwconfig ' + self.wireless_interface + ' mode ad-hoc')
		misc.Run('iwconfig ' + self.wireless_interface + ' channel ' + channel)
		misc.Run('iwconfig ' + self.wireless_interface + ' essid ' + essid)
		#Right now it just assumes you're using WEP
		if encused == True:
			misc.Run('iwconfig ' + self.wireless_interface + ' key ' + key)

		misc.Run('ifconfig ' + self.wireless_interface + ' up')
		misc.Run('ifconfig ' + self.wireless_interface + ' inet ' + ip)

		#also just assume that the netmask is 255.255.255.0, it simplifies ICS
		misc.Run('ifconfig ' + self.wireless_interface + ' netmask 255.255.255.0')

		ip_parts = misc.IsValidIP(ip)

		if ics and ip_parts:
			#set up internet connection sharing here
			#flush the forward tables
			misc.Run('iptables -F FORWARD')
			misc.Run('iptables -N fw-interfaces')
			misc.Run('iptables -N fw-open')
			misc.Run('iptables -F fw-interfaces')
			misc.Run('iptables -F fw-open')
			misc.Run('iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu')
			misc.Run('iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT')
			misc.Run('iptables -A FORWARD -j fw-interfaces ')
			misc.Run('iptables -A FORWARD -j fw-open ')
			misc.Run('iptables -A FORWARD -j REJECT --reject-with icmp-host-unreachable')
			misc.Run('iptables -P FORWARD DROP')
			misc.Run('iptables -A fw-interfaces -i ' + self.wireless_interface + ' -j ACCEPT')
			basic_ip = '.'.join(ip_parts[0:3]) + '.0' #not sure that basic_ip is a good name
			misc.Run('iptables -t nat -A POSTROUTING -s ' + basic_ip + '/255.255.255.0 -o ' + self.wired_interface + ' -j MASQUERADE')
			misc.Run('echo 1 > /proc/sys/net/ipv4/ip_forward') #enable routing
	#end function CreateAdHocNetwork

	def DetectWirelessInterface(self):
		return misc.RunRegex(re.compile('(\w*)\s*\w*\s*[a-zA-Z0-9.-_]*\s*(?=ESSID)',re.DOTALL | re.I | re.M  | re.S),misc.Run("iwconfig"))

	def Disconnect(self):
		misc.Run('ifconfig ' + self.wired_interface + ' 0.0.0.0')
		misc.Run('ifconfig ' + self.wired_interface + ' down')
		misc.Run('ifconfig ' + self.wireless_interface + ' 0.0.0.0')
		misc.Run('ifconfig ' + self.wireless_interface + ' down')


#end class Wireless

class Wired:

	wireless_interface = None
	wired_interface = None
	ConnectingThread = None

	def GetIP(self):
		output = misc.Run("ifconfig " + self.wired_interface)
		ip_pattern	= re.compile(r'inet [Aa]d?dr[^.]*:([^.]*\.[^.]*\.[^.]*\.[0-9]*)',re.S)
		return misc.RunRegex(ip_pattern,output)

	def CheckPluggedIn(self):
		mii_tool_data = misc.Run( 'mii-tool ' + self.wired_interface,True)
		if not misc.RunRegex(re.compile('(Invalid argument)',re.DOTALL | re.I | re.M | re.S),mii_tool_data) == None:
			print 'wired interface appears down, putting up for mii-tool check'
			misc.Run( 'ifconfig ' + self.wired_interface + ' up' )
		mii_tool_data = misc.Run( 'mii-tool ' + self.wired_interface)
		if not misc.RunRegex(re.compile('(link ok)',re.DOTALL | re.I | re.M  | re.S),mii_tool_data) == None:
			return True
		else:
			return False
	#end function CheckPluggedIn

	def Connect(self,network):
		#call the thread, so we don't hang up the entire works
		self.ConnectingThread = self.ConnectThread(network,self.wireless_interface,self.wired_interface)
		self.ConnectingThread.start()
		return True
	#end function Connect

	class ConnectThread(threading.Thread):
		#wired interface connect thread
		lock = thread.allocate_lock()
		ConnectingMessage = None
		ShouldDie = False

		def __init__(self,network,wireless,wired):
			threading.Thread.__init__(self)
			self.network = network
			self.wireless_interface = wireless
			self.wired_interface = wired
			self.IsConnecting = False
			self.lock.acquire()
			self.ConnectingMessage = 'interface_down'
			self.lock.release()
		#end function __init__

		def GetStatus(self):
			self.lock.acquire()
			print "	...lock acquired..."
			message = self.ConnectingMessage
			self.lock.release()
			print "	...lock released..."
			return message

		def run(self):
			#we don't touch the wifi interface
			#but we do remove all wifi entries from the
			#routing table

			self.IsConnecting = True
			network = self.network 

			#put it down
			self.lock.acquire()
			self.ConnectingMessage = 'interface_down'
			self.lock.release()
			print "interface down...", self.wired_interface
			misc.Run("ifconfig " + self.wired_interface + " down")

			#set a false ip so that when we set the real one, the correct
			#routing entry is created
			self.lock.acquire()
			self.ConnectingMessage = 'resetting_ip_address'
			self.lock.release()
			print "setting false ip... 0.0.0.0 on", self.wired_interface
			misc.Run("ifconfig " + self.wired_interface + " 0.0.0.0")
			misc.Run("ifconfig " + self.wireless_interface + " 0.0.0.0")

			#bring it up
			self.lock.acquire()
			self.ConnectingMessage = 'interface_up'
			self.lock.release()
			print "interface up...", self.wired_interface
			misc.Run("ifconfig " + self.wired_interface + " up")

			print "killing wpa_supplicant, dhclient, dhclient3"
			self.lock.acquire()
			self.ConnectingMessage = 'removing_old_connection'
			self.lock.release()
			misc.Run("killall dhclient dhclient3 wpa_supplicant")

			print "flushing the routing table..."
			self.lock.acquire()
			self.ConnectingMessage = 'flushing_routing_table'
			self.lock.release()
			misc.Run("ip route flush dev " + self.wireless_interface)
			misc.Run("ip route flush dev " + self.wired_interface)

			if not network.get("broadcast") == None:
				self.lock.acquire()
				self.ConnectingMessage = 'setting_broadcast_address'
				self.lock.release()
				print "setting the broadcast address..." + network["broadcast"]
				misc.Run("ifconfig " + self.wired_interface + " broadcast " + network["broadcast"])

			if not network.get("dns1") == None:
				self.lock.acquire()
				self.ConnectingMessage = 'setting_static_dns'
				self.lock.release()
				print "setting the first dns server...", network["dns1"]
				resolv = open("/etc/resolv.conf","w")
				misc.WriteLine(resolv,"nameserver " + network["dns1"])
				if not network.get("dns2") == None:
					print "setting the second dns server...", network["dns2"]
					misc.WriteLine(resolv,"nameserver " + network["dns2"])
				if not network.get("dns3") == None:
					print "setting the third dns server..."
					misc.WriteLine(resolv,"nameserver " + network["dns3"]))

			if not network.get("ip") == None:
				self.lock.acquire()
				self.ConnectingMessage = 'setting_static_ip'
				self.lock.release()
				print "setting static ips...", network["ip"]
				misc.Run("ifconfig " + self.wired_interface + " " + network["ip"])
				misc.Run("ifconfig " + self.wired_interface + " netmask " + network["netmask"])
				print "adding default gateway..." + network["gateway"]
				misc.Run("route add default gw " + network["gateway"])
			else:
				#run dhcp...
				self.lock.acquire()
				self.ConnectingMessage = 'running_dhcp'
				self.lock.release()
				print "running dhcp..."
				if not self.ShouldDie:
					misc.Run("dhclient " + self.wired_interface)

			self.lock.acquire()
			self.ConnectingMessage = 'done'
			self.lock.release()
			self.IsConnecting = False
		#end function run

