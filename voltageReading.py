import datetime, time

import requests, json

import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008

# Hardware SPI configuration for ADC (MCP3008):
SPI_PORT   = 0
SPI_DEVICE = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))
states = {} 

states["description"] = []                                   
postUrl = 'http://spaceplants.datascientists.com/web/rest/public/savelog'
headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
values = []
location_identifier= "KfvevR54WK1680028300"
def main():
    now = datetime.datetime.now()
    states['date'] = str(now)
    
    states["type"] = "INFO"
    states["description"].append(location_identifier)
    #states["description"].append("testing")
    sum = [0]*3
    sampleNum = 10
    sampleTime = 0.1
    states["description"].append("raw ADC values")
    for i in range(3): #for each voltage
        #measure a few times to get the average reading        
        for samples in range(sampleNum):
            #sum[i] += i*300
            sum[i] += mcp.read_adc(i)
            time.sleep(sampleTime)
        #print sum            
        sum[i] = sum[i]/sampleNum
        #print sum   
        values.append(sum[i])
        states["description"].append(values[i])
        
        
    #check values make sense here?
    #perhaps could check for high or low voltages and throw warnings? 
    states["description"].append("battery voltages")
    states["description"].append(values[0]*3.3/1023*(22000+6800)/6800)
    states["description"].append(values[1]*3.3/1023*(22000+6800)/6800)
    states["description"].append(values[2]*3.3/1023*(22000+6800)/6800) 
                                              
    # print states
    states['description'] = ','.join(map(str, states['description']))
    print states
    json_data = json.dumps(states)
    
    
    #what happens if internet connection has a problem or if there's a problem with server?
    #do we need error catching here? 
    #store voltages locally in file till able to connect again to internet
    #https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module
    try:
        r = requests.post(postUrl, data=json_data, headers=headers)
        print(r.status_code, r.reason)
        
        #read the file and see if it's empty - nothing to upload
        #if not empty then we have old data to upload?
        
    except requests.exceptions.ConnectionError:
        print "request failed - writing to file"
        #save data locally
        #https://stackoverflow.com/questions/12994442/appending-data-to-a-json-file-in-python
        with open('voltages.txt', 'a') as outfile:
            json.dump(states, outfile)
            #https://stackoverflow.com/questions/17055117/python-json-dump-append-to-txt-with-each-variable-on-new-line
            outfile.write('\n')
            
        #Do I need to close the file?
        #with seems to take care of this! https://stackoverflow.com/questions/1369526/what-is-the-python-keyword-with-used-for
    
try:
    main()
except KeyboardInterrupt:
    print "interuppted"
        
print states
print 'voltage reading done, bye'
    
