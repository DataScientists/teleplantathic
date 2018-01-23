import time, datetime, calendar
from pytz import timezone

import requests, json
import RPi.GPIO as GPIO

import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008

# Hardware SPI configuration for ADC (MCP3008):
SPI_PORT   = 0
SPI_DEVICE = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))
voltageStates = {} 
voltageStates["description"] = []                                   
postUrl = 'http://spaceplants.datascientists.com/web/rest/public/savelog'
headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

#pumping code
Relay_Ch1 = 21
Relay_Ch2 = 26
Relay_Ch3 = 19
Relay_Ch4 = 13

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(Relay_Ch1,GPIO.OUT)
GPIO.setup(Relay_Ch2,GPIO.OUT)
GPIO.setup(Relay_Ch3,GPIO.OUT)
GPIO.setup(Relay_Ch4,GPIO.OUT)

GPIO.output(Relay_Ch1,GPIO.HIGH)
GPIO.output(Relay_Ch2,GPIO.HIGH)
GPIO.output(Relay_Ch3,GPIO.HIGH)
GPIO.output(Relay_Ch4,GPIO.HIGH)

#GPIO.output(Relay_Ch1,GPIO.LOW)
#time.sleep(3)
#GPIO.output(Relay_Ch1,GPIO.HIGH)
                            
#time.sleep(2)
#GPIO.output(Relay_Ch1,GPIO.LOW)
#time.sleep(2)
#GPIO.output(Relay_Ch2,GPIO.LOW)
#time.sleep(2)
#GPIO.output(Relay_Ch3,GPIO.LOW)
#time.sleep(2)
#GPIO.output(Relay_Ch4,GPIO.LOW)

running = True
pumpStates = {} 
pumpStates["description"] = []
pumpingCount = 0   #add to count if it turns on  - perhaps keep track of this each day? Store locally?


scheduleUrl = "http://spaceplants.datascientists.com/web/rest/public/wateringschedule?location_identifier="
print scheduleUrl 
location_identifier= "ozr7Zc7VBH1500963678811"
scheduleUrl = scheduleUrl + location_identifier
print scheduleUrl

def pumpWatering():
    values = []
    #GPIO.output(Relay_Ch1,GPIO.LOW)
    #time.sleep(2*60)
    #GPIO.output(Relay_Ch1,GPIO.HIGH)
    
    global running
    global pumpingCount
    pumpState = "default"
    pumpStates["description"].append(location_identifier)
    pumpStates["description"].append("pump status check")
        

    try:
        response = requests.get(scheduleUrl)
        #successful so carry on using response
        data = json.loads(response.text)
        
        #what if this fails to load? How to catch this error?
        print data
        #Perhaps could store this locally? use this local copy if unable to connect to internet for a few hours? 
        #Is there a period of time after which plants usually need to be watered? E.g. every 6 hours? 12 hours? Guess it depends on the rain? 
        # pumpStates['schedule_url'] = scheduleUrl
        # pumpStates['schedule pulled from internet'] = data
        # pumpStates['location identifier'] = location_identifier
        if 'timezone' in data.keys():
            print 'timezone is ', data['timezone']
            ourTimeZone = data['timezone']
            now = datetime.datetime.now(timezone(data['timezone']))
        else:
            print "timezone not found"
            pumpStates["type"] = "WARNING"
            pumpStates["description"].append("Time zone not found")
            now = datetime.datetime.now()
            ourTimeZone = "local"
        
        pumpStates['date'] = str(now)
        print 'time in the timezone is: ', now
        for i in data:  #go through the pump schedule
            # print i, calendar.day_name[datetime.datetime.today().weekday()].lower()
            
            #check if today matches any of the days in schedule
            if calendar.day_name[now.weekday()].lower() == i: 
                print 'found ', calendar.day_name[now.weekday()], 'in pump schedule'
                print data[i] 
                # print len(data[i])
            
                #if there's something scheduled on this day
                if len(data[i]) <= 0: 
                    #empty data today?
                    print 'Nothing set for today'
                    pumpStates["type"] = "ERROR"
                    pumpStates["description"].append("Watering schedule not found")
                    running = False
                    pumpState = "not running"
                if len(data[i]) > 0: 
                    print 'Need to water at least once today!'
                    #go through list of times on the day
                    for j in data[i]: 
                        # print j
                        # print type(j['timing']['starttime'].encode('UTF-8'))
                    
                        start_hour, start_minute = j['timing']['starttime'].encode('UTF-8').split(':')
                        run_time = j['timing']['runtime']  #already an int apparently! can't do the .encode afterwards!
                        # print 'start_hour type', type(start_hour)
                        # print 'start_min type', type(start_minute)
                        # https://stackoverflow.com/questions/10663720/converting-a-time-string-to-seconds-in-python

                        # start_hour, start_minute = j['timing']['starttime'].encode('UTF-8').split(':')
                        start_hour = int(start_hour)
                        start_minute = int(start_minute)
                        # print start_hour*3600, start_minute*60  #prints copies of this meaning repeating strings.. 
                    
                        # print type(start_hour), type(start_minute)  #prints copies of this meaning repeating strings.. 
                    
                        # https://stackoverflow.com/questions/30071886/how-to-get-current-time-in-python-and-break-up-into-year-month-day-hour-minu
                        if 'timezone' in data.keys():
                            now = datetime.datetime.now(timezone(data['timezone']))
                        else:
                            now = datetime.datetime.now()

                        print now
                        # print type(now.hour)
                        # print type(now.minute)
                        
                        # print now.hour, now.minute
                        # print 'start time seconds', start_hour*3600+start_minute*60
                        # print 'now in seconds', now.hour*3600 + now.minute*60  #forgot to add on the seconds! 
                        # print 'end time in seconds' start_hour*3600+start_minute*60 + run_time*60
                        # print 'milliseconds', now.milliseconds
                        # print 'microseconds', now.microseconds
                        # if((start_hour*3600 + start_minute*60) == now.hour*3600 + now.minute*60 + now.second)
                        if((start_hour*3600+start_minute*60)  <= (now.hour*3600 + now.minute*60 + now.second) <=  (start_hour*3600+start_minute*60 + run_time*60)): 
                            pumpState = "turning on"
                            print pumpState
                            pumpStates["type"] = "INFO"
                            pumpStates["description"].append("turning on")
                            # pumpStates[str(now)] = pumpState
                            GPIO.output(Relay_Ch1,GPIO.LOW)
                            time.sleep(run_time*60)
                            
                            if 'timezone' in data.keys():
                                now = datetime.datetime.now(timezone(data['timezone']))
                            else:
                                now = datetime.datetime.now()
                            GPIO.output(Relay_Ch1,GPIO.HIGH)
                            running = False 
                            pumpState = "turning off"
                            pumpStates["type"] = "INFO"
                            pumpStates["description"].append("turning off")

                            # pumpStates[str(now)] = pumpState
                            
                            pumpingCount += 1
                            # https://stackoverflow.com/questions/510348/how-can-i-make-a-time-delay-in-python
                        else: 
                            GPIO.output(Relay_Ch1,GPIO.HIGH)
                            running = False 
                            pumpState = "not running"
        if pumpingCount == 0:
            # no pumping just then..
            # pumpStates[str(now)] = pumpState
            print "pumpCount = 0"
        
        # print pumpStates
        pumpStates['description'] = ','.join(map(str, pumpStates['description'])) 
        print pumpStates
        json_data = json.dumps(pumpStates)
        try:
            r = requests.post(postUrl, data=json_data, headers=headers)
            print(r.status_code, r.reason)
            
            #read the file and see if it's empty - nothing to upload
            #if not empty then we have old data to upload?
            
        except requests.exceptions.ConnectionError:
            print "request failed - writing to file"
            #save data locally
            #https://stackoverflow.com/questions/12994442/appending-data-to-a-json-file-in-python
            with open('log.txt', 'a') as outfile:
                json.dump(pumpStates, outfile)
                #https://stackoverflow.com/questions/17055117/python-json-dump-append-to-txt-with-each-variable-on-new-line
                outfile.write('\n')
        
        #Do I need to close the file?
        #with seems to take care of this! https://stackoverflow.com/questions/1369526/what-is-the-python-keyword-with-used-for
    
    #perhaps have default timings for each week in case of no internet connection e.g. 3 times a day for 1 min, 7 days a week. 
    except requests.exceptions.ConnectionError:
        #failed to get schedule. Load local one? 
        #use a default data or 1 from a file? But need to ensure don't water too many times today?
        #keep track of how many times we're watering? 
        print "connection error retrieving schedule"
        now = datetime.datetime.now()        
        pumpStates['date'] = str(now)
        
        #write time to file?
        running = False


def voltageReading():
    values = []
    now = datetime.datetime.now()
    voltageStates['date'] = str(now)
    
    voltageStates["type"] = "INFO"
    voltageStates["description"].append(location_identifier)
    #voltageStates["description"].append("testing")
    sum = [0]*3
    sampleNum = 10
    sampleTime = 0.1
    voltageStates["description"].append("raw ADC values")
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
        voltageStates["description"].append(values[i])
        
        
    #check values make sense here?
    #perhaps could check for high or low voltages and throw warnings? 
    voltageStates["description"].append("battery voltages")
    voltageStates["description"].append(values[0]*3.3/1023*(22000+6800)/6800)
    voltageStates["description"].append(values[1]*3.3/1023*(22000+6800)/6800)
    voltageStates["description"].append(values[2]*3.3/1023*(22000+6800)/6800) 
                                              
    # print voltageStates
    voltageStates['description'] = ','.join(map(str, voltageStates['description']))
    print voltageStates
    json_data = json.dumps(voltageStates)
    
    
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
        with open('log.txt', 'a') as outfile:
            json.dump(voltageStates, outfile)
            #https://stackoverflow.com/questions/17055117/python-json-dump-append-to-txt-with-each-variable-on-new-line
            outfile.write('\n')
            
        #Do I need to close the file?
        #with seems to take care of this! https://stackoverflow.com/questions/1369526/what-is-the-python-keyword-with-used-for
    
while running:
    try:
        pumpWatering()
    except KeyboardInterrupt:
        GPIO.cleanup()
        running = False
try:
    voltageReading()
except KeyboardInterrupt:
    print "interuppted"   
        
GPIO.cleanup()
print pumpStates
print 'all done, bye'
