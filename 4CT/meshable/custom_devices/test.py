seconds = 789
hours = int((seconds / 3600))

print hours
seconds = 4000
hours = int((seconds / 3600))

print hours

"""from xml.dom.minidom import parseString



msg ="<sci_request version='1.0'><send_message><targets><device id='00000000-00000000-00409DFF-FF3FD6EF'/></targets><rci_request version='1.1'><do_command target='dia'><data><channel_dump name='mc3_[00:13:a2:00:40:86:00:be]!.BOT' value='9000'/></data></do_command></rci_request></send_message></sci_request>"


mac = msg.split("id=")
mac = mac[1]
mac = mac[19:36]
print mac

#setData = msg.split("<do_command target='dia'>")

#data = setData[1].replace("</do_command></rci_request></send_message></sci_request>'", "")
#print data


e = parseString(msg)
deviceList = e.getElementsByTagName('device')
MAC = deviceList[0].attributes['id'].value
MAC = MAC.replace("00000000-00000000-", "") 
MAC = MAC.replace("FF-FF", "")
print MAC
data = e.getElementsByTagName('do_command') 
data = data[0].childNodes
data = data[0].toxml()
print data




#print data[0]. """