import time, datetime, calendar
from pytz import timezone
import requests, json

postUrl = 'http://spaceplants.datascientists.com/web/rest/public/savelog'
headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

try:
    import config
    location_identifier= config.location_identifier
except ImportError:
    location_identifier= 'default'    

#put schedulrUrl into config?
scheduleUrl = "http://spaceplants.datascientists.com/web/rest/public/wateringschedule?location_identifier="
scheduleUrl = scheduleUrl + location_identifier
print scheduleUrl

# Hardware SPI configuration for ADC (MCP3008):
voltageRunning = True
voltageStates = {} 
voltageStates["description"] = []     

pumpRunning = True
pumpStates = {} 
pumpStates["description"] = []
pumpingCount = 0   #add to count if it turns on  - perhaps keep track of this each day? Store locally?

#default timezone. Get's changed to True if we get the timezone via watering schedule
timezoneFound = False
ourTimezone = "local"  #by default

#https://stackoverflow.com/questions/3131217/error-handling-when-importing-modules
try:
    import RPi.GPIO as GPIO
except ImportError:
    #what now?
    #don't run pumpWatering function
    logImportError("import RPI.GPIO Error")
    pumpRunning = False

try:
    import Adafruit_GPIO.SPI as SPI
except ImportError:
    #don't run pumpWatering..
    logImportError("import Adafruit_GPIO.SPI Error")
    voltageRunning = False

try:    
    import Adafruit_MCP3008
except ImportError:
    logImportError("import Adafruit_MCP3008 Error")   


try:
    # https://stackoverflow.com/questions/35788729/start-node-app-from-python-script
    import subprocess
    # can use this later to run the node file..  
    # subprocess.call('sudo node ./node-flower-bridge/start.js')
except ImportError:
    logImportError("subprocess Error")   


def logImportError(errorMessage):
    importLog = {} 
    importLog["description"] = []
    now = getRightTime()        
    importLog['date'] = str(now)
    importLog["type"] = "ERROR"
    importLog["description"].append(location_identifier)
    importLog["description"].append(errorMessage)
    importLog["description"].append("default_timezone")
    logging(posturl, importLog)        
    

#pumping code
def setupRelays():
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


def pumpWatering():
    setupRelays()
    values = []
    
    global pumpRunning
    global pumpingCount
    global timezoneFound 
    global ourTimezone

    pumpState = "default"
    pumpStates["description"].append(location_identifier)
    pumpStates["description"].append("pump status check")
    print '\n\n Pump check'
    
    
    try:
        response = requests.get(scheduleUrl)
        #successful so carry on using response
        data = json.loads(response.text)
        
        #what if this fails to load? How to catch this error?
        print data
        #Perhaps could store this locally? use this local copy if unable to connect to internet for a few hours? 
        #Is there a period of time after which plants usually need to be watered? E.g. every 6 hours? 12 hours? Guess it depends on the rain? 
        if 'timezone' in data.keys():
            print 'timezone is ', data['timezone']
            timezoneFound = True
            ourTimezone = data['timezone']

        else:
            print "timezone not found"
            # pumpStates["type"] = "WARNING"
            pumpStates["description"].append("No time zone provided - using local")
            # should we log a warning here?     
            ourTimezone = "local"
            timezoneFound = False

        now = getRightTime()
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
                    pumpStates["type"] = "WARNING"
                    pumpStates["description"].append("Watering schedule empty")
                    pumpRunning = False
                    pumpState = "not running"
                if len(data[i]) > 0: 
                    print 'Need to water at least once today!'
                    #go through list of times on the day
                    for j in data[i]:                     
                        start_hour, start_minute = j['timing']['starttime'].encode('UTF-8').split(':')
                        run_time = j['timing']['runtime']  #already an int apparently! can't do the .encode afterwards!

                        type(run_time)
                        start_hour = int(start_hour)
                        start_minute = int(start_minute)

                        now = getRightTime()
                        print now
                        if((start_hour*3600+start_minute*60)  <= (now.hour*3600 + now.minute*60 + now.second) <=  (start_hour*3600+start_minute*60 + run_time*60)): 
                            pumpState = "turning on"
                            print pumpState
                            pumpStates["type"] = "INFO"
                            onTimeString = "tunrning on for" + str(run_time) + " minutes"
                            pumpStates["description"].append(onTimeString)
                            # pumpStates[str(now)] = pumpState
                            GPIO.output(Relay_Ch1,GPIO.LOW)
                            print 'for: ' + run_time + ' minutes'
                            time.sleep(run_time*60)
                            
                            now = getRightTime()
                            GPIO.output(Relay_Ch1,GPIO.HIGH)
                            pumpRunning = False 
                            pumpState = "turning off"
                            pumpStates["type"] = "INFO"
                            pumpStates["description"].append("turning off")                            
                            pumpingCount += 1
                        else: 
                            GPIO.output(Relay_Ch1,GPIO.HIGH)
                            pumpRunning = False 
                            pumpState = "not running"
        if pumpingCount == 0:
            # no pumping just then..
            print "pumpCount = 0"
        
        #log to website or to file or print out if both fail
        logging(posturl, pumpStates)        
    
    
    #failed to get schedule. Load local one? 
    except requests.exceptions.ConnectionError:
        #perhaps use a default schedule from a file? But need to ensure don't water too many times each day?
        #keep track of how many times we're watering? Or perhaps do that on server side? 
        print "connection error retrieving schedule"
        now = getRightTime()      
        pumpStates['date'] = str(now)
        pumpStates["type"] = "ERROR"
        pumpStates["description"].append("Water Schedule Connection Error")
        print pumpStates
        pumpRunning = False
        logging(posturl, pumpStates) 

    #need to schedule when to run this function next? 

def voltageReading():
    print '\n\n Voltage Reading'
    values = []
    SPI_PORT   = 0
    SPI_DEVICE = 0
    mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))

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

    logging(posturl, voltageStates)


def logging(url, data): 
    #join the description into 1 comma separated string
    data['description'] = ','.join(map(str, data['description'])) 
    print data

    try:
        json_data = json.dumps(data)
        r = requests.post(url, json_data, headers)
        print(r.status_code, r.reason)
        
        #read the file and see if it's empty - nothing to upload
        #if not empty then we have old data to upload?
        
    except requests.exceptions.ConnectionError:
        print "request failed - writing to file"
        #save data locally
        #https://stackoverflow.com/questions/12994442/appending-data-to-a-json-file-in-python

        # https://stackoverflow.com/questions/713794/catching-an-exception-while-using-a-python-with-statement
        #error catching with statements
        try:
            with open('log.txt', 'a') as outfile:
                data = data + 'connectionError'
                json.dump(data, outfile)
                #https://stackoverflow.com/questions/17055117/python-json-dump-append-to-txt-with-each-variable-on-new-line
                outfile.write('\n')
        
        except Exception as error: 
            data = data + ',fileOutputFailed'   
            print data    
        #Do I need to close the file?
        #with seems to take care of this! https://stackoverflow.com/questions/1369526/what-is-the-python-keyword-with-used-for

def getRightTime():
    if timezoneFound:
        return datetime.datetime.now(timezone(ourTimezone))
    else:
        return datetime.datetime.now()


#need to run code for flower power if not running? 
while pumpRunning:
    try:
        pumpWatering()
    except KeyboardInterrupt:
        GPIO.cleanup()
        running = False

while voltageRunning: 
    try:
        voltageReading()
    except KeyboardInterrupt:
        print "interuppted"   
        
GPIO.cleanup()
print pumpStates
print 'all done, bye'