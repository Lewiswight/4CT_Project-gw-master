import urllib
import pickle
url = "http://devbuildinglynx.apphb.com/api/gateways?macaddressForTimezone=" + "00409DFF-FF45871E"
         
try:
    f = urllib.urlopen(url)
except:
   self.w_retry += 1
   print "Error opening url"

try:
    s = f.read()
    print s
    offset = ""
    place_temp = s.find("gmt_offset")
    temp_offset = s[place_temp + 12 : place_temp + 20]
    for i in temp_offset:
        if i != ",":
            offset = offset + i 
        else:
            break
    offset = int(offset)
    pickle.dump( offset, open( "offset.p", "wb" ) )
    print (50000 + int(offset))
except:
    pass


favorite_color = pickle.load( open( "offset.p", "rb" ) )
print "here it is from the pickle"
print favorite_color



