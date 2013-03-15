'''
Created on Mar 20, 2012

@author: Lewis
'''
#import urllib
#from xml.dom import minidom 
""""



WEATHER_URL = 'http://xml.weather.yahoo.com/forecastrss?p=%s'
WEATHER_NS = 'http://xml.weather.yahoo.com/ns/rss/1.0'

def weather_for_zip(zip_code):
    url = WEATHER_URL % zip_code
    dom = minidom.parse(urllib.urlopen(url))
 #   print dom
    forecasts = []
    for node in dom.getElementsByTagName('channel'):
        for nod in node.childNodes:
            print "name:"
            try:
                print nod.tagName
                print nod.nodeValue 
                print nod.value
            except:
            	print nod
        forecasts.append({
            'date': node.getAttribute('date'),
            'low': node.getAttribute('low'),
            'high': node.getAttribute('high'),
            'condition': node.getAttribute('text')
        })
        
    ycondition = dom.getElementsByTagNameNS(WEATHER_NS, 'condition')[0]
    return {
        'current_condition': ycondition.getAttribute('text'),
        'current_temp': ycondition.getAttribute('temp'),
        'forecasts': forecasts,
        'title': dom.getElementsByTagName('title')[0].firstChild.data
    }
        
from pprint import pprint
pprint(weather_for_zip(66044))
"""