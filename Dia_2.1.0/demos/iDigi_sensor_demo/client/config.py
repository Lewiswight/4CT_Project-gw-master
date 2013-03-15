

################### iDigi options ###################

# iDigi server address
host = "sd1-na.idigi.com"
# iDigi username
user="password"
# iDigi password
password="password"
# Poll rate in seconds, time between eXist requests
poll_interval = 1

################### Locale options ###################

# temperature unit, C or F
temp_unit = "F" 
# language setting.  This string will be appended to the route lists below. 
# For a new language new html files will need to be created.
language="english"

################### optional options ###################

# [optional] the gateway, this is only defined on systems that
# will be for only a single gateway.  if undeclared the user
# will be able to pick the gateway they want from the webui
#gateway = "00000000-00000000-00409DFF-FF382CFC "

# [optional] specify sensors wanted to monitor
# if this is commented out the server will auto-discover
# _all_ sensors connected to gateway
#sensors = [ 'lth_sensor_1.light', 
#            'lth_sensor_1.temperature', 
#            'lth_sensor_1.humidity' ]

# [optional] can rename the title over a flash widget
sensor_alias={}
sensor_alias["lth_sensor_1.temperature"] = "temp"

#####################################################################################
##############################--# Do Not Modify below here #--#######################
#####################################################################################
import base64
auth = base64.encodestring( "%s:%s"%(user,password) )[:-1]
# route translations
#  a HTTP GET to server will have URL replaced by the value if the key in route
#  is within the URL
#
# Change the suffix of files using the language variable as needed to reflect in-country language support.
route["/0"] = "/demo.py"
route["/1"] = "/sensor_" + language + ".html"
route["/2"] = "/localarea_" + language + ".html"
route["/3"] = "/gateways_" + language + ".html"
route["/4"] = "/widearea_" + language + ".html"
route["/5"] = "/idigi_" + language + ".html"
route["/6"] = "/applications_" + language + ".html"
route["/flash/flashdata.php"] = "/flash/flashdata.py" #fix for bug in open gauges