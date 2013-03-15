
channel = request["funcName"][0]
sample_data="value=0&range=1&units=waiting"

cwm = http_helper.CWMControl( host, auth, self.dev_id, channel)
sample = cwm.retrieve_sample( self.dev_id ,channel )

if not len(sample) == 0 :
    
    # fix for opengauges meter bug
    if "%s"%sample["value"] == "0.0":
        sample["value"] = 0.00001 # no division by 0
    ##
    
    # sample data changes based on the type of widget
    sample_data = "value=%s&"%sample["value"]
    
    data_range = 0
    units = "units"
    if sample["unit"] == "V":
      data_range = 12
      units = "volts"
    elif sample["unit"] == "C":
      data_range = 45
      if temp_unit=="F":
          sample_data = "value=%s&"%( (9.0/5.0)*float(sample["value"])+32 )
          data_range = 110
      
      units = "degrees"
    elif sample["unit"] == "brightness":
      data_range = 1000  
      units = "brightness"
    elif sample["unit"] == "A":
      data_range = 20
      units = "amps" 
    elif sample["unit"] == "%":
      sample_data = "value=%s&"%sample["value"][:2]
      data_range = 100 
      units = "percent"
      
    sample_data = sample_data + "range=%s&units=%s"%(data_range, units)
