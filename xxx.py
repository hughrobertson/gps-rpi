#!/usr/bin/python
'''
Created on 19 Mar 2014
updated on 31 Mar 2014
updated on 1p April 2014
updated on 3p April 2014
updated on 4a April 2014
@author: hugh
'''
global version
version = "3.04a  " 

import sys
import serial
import os
import re
import time
import mosquitto
import socket
#import commands

global gpsParams
global errorLog
global logFile
global dataFile
global serin
global serout 
global gpsData
#global GPGGA
global gpsOKflag
global lastTime
global lastDate
global messageUpdate
global newData
global updateCount
global mqttGo
global GPGGAdata
global GPVTGdata
global GPPMCdata
global gpsValidData
global mqttl


gpsParams = {"time":"0","nor":"0","lat":"0","east":"0","quality":"0","altitude":"0"} 

serialdevIn     = '/dev/ttyUSB0'
serialdevout    = '/dev/ttyUSB1'

result          ="xxx"

broker =  "mqtt.for-our.info"#"test.mosquitto.org"#"192.168.2.96"# "localhost" #"192.168.2.96"
PublishAt = "kelvinweb/gps/raw"

brokerLocal  = "127.0.0.1"
publishLocal = "/gps/data"
publishLocal2 = "/gps/data2"
publishLocal3 = "/gps/data3"
publishLocal4 = "/gps/data4"   # error messages


port = 1883
 
 
#MQTT callbacks
 
def on_connect(mosq, obj, rc):
    if rc == 0:
    #rc 0 successful connect
        print "Connected"
    else:
        raise Exception
 
 
def on_publish(mosq, obj, mid):
    #print("Message "+str(mid)+" published.")
    pass
 
#called on exit
#close serial, disconnect MQTT
def on_disconnect(mosq, obj, rc):
    print("Disconnected successfully.")



def chksum_nmea(sentence):
    #print "chksum_nmea\n"
    
    cksum = sentence[len(sentence) - 4:]
    
    chksumdata = re.sub("(\n|\r\n)","", sentence[sentence.find("$")+1:sentence.find("*")])
    
    # Initializing our first XOR value
    csum = 0
    
    for c in chksumdata:
        csum ^= ord(c)

    # Do we have a valid checksum?
    if hex(csum) == hex(int(cksum, 16)):
        return True
    return False

def errorHandle(message):
    global errorLog
    global gpsParams
    global lastTime
    global lastDate
    global mqttl
    try:
        cmessage = lastDate + " " + lastTime + " " + message+"\n"
        print cmessage
        errorLog.write(cmessage)
        mqttl.publish(publishLocal4,cmessage)
    except:
        print "no errorlog    ", message
    
def restartProg(): 
    """Restarts the current program.
    Note: this function does not return. Any cleanup action (like
    saving data) must be done before calling this function."""
    python = sys.executable
    os.execl(python, python, * sys.argv)
    
def readData():
    global errorLog
    global logFile
    global gpsData
    global gpsOKflag
    global serin

    result=False
    #print "readData\n"
    #print serin.portstr ,
    #print serin.isOpen(),
    try:
        bytesToRead = serin.inWaiting()
    #print "bytesToRead",bytesToRead
    except:
        error =   "GPS unplugged"
        errorHandle(error)
        serin.close()
        time.sleep(2)
        restartProg()

    try:
        gpsData = serin.readline()
        gpsOKflag =True
    except:
        gpsOKflag =False
        error =  "no valid gps data"
        errorHandle(error)
        time.sleep(1)
    
    if(gpsOKflag ==True):
        try:
            result = chksum_nmea(gpsData)
        except:
            error =  "checksum data"
            errorHandle(error)
            result=False
        finally:
            if result == True:    
                #print gpsData,
                #logFile.write(gpsData)
                pass
            else:
                error =  "checksum error"
                errorHandle(error)
                result==False
    #print "gpsOKflag",gpsOKflag,"result",result
    return result     
 
def cleanup():
    
    print "Ending and cleaning up\n"
    #serin.close()
    #serout.close()
    #mqttc.disconnect()
    
def getGPdata():
    global gpsParams
    global gpsData
    global gpsOKflag
    global lastTime
    global lastDate
    global newData
    global updateCount
    global messageUpdate
    global mqttGo
    global GPGGAdata
    global GPVTGdata
    global GPPMCdata
    #print "getGPdata\n"
    global gpsValidData
    
    status = False
    y = ''
    for line in gpsData.split('\n') :
        if line.startswith( '$GPGGA' ) :
            qual = line.strip().split(',')[6:7]
            x=y.join(qual)
            #print ">>>>>>>>>>>>>>>>>",x
            if x == '1':
                gpsOKflag  =True
            else:
                gpsOKflag =False

            
            if gpsOKflag == True:
                tim,lat, nnn, lon,eee,quality,nsat, accu,alti= line.strip().split(',')[1:10]
                sats = int(nsat)
                if sats <4:
                    print "less than 4 satellites", sats
                    gpsValidData=False
                    gpsOKflag =False
                else:
                    #print "sats = ",sats
                    gpsValidData=True
                    #print "time:",tim,
                    lastTime = tim
                    #print nnn,"lat" ,  lat,
                    #print eee,"long",  lon,
                    #print "quality:",quality,
                    #print"altitude",alti
                    gpsParams = {"time":tim,"north":nnn,"lat":lat,"east":eee,"lon":lon,"quality":quality, "altitude":alti,"sats":nsat}
                    GPGGAdata = line
                    gpsOKflag = True
    
                    newData=  ",lat:" + str(lat) + ",long:" +  str(lon) + ",altitude:" +  str(alti)
                    #print newData
                    status = True


        elif line.startswith( '$GPRMC' ) :
            if gpsOKflag == True:
                tim2,valid, lat2, n2,lon2,w2,speed,course, date = line.strip().split(',')[1:10]
                lastTime=tim2
                #print "valid:",valid,
                #print "speed" ,  speed,
                #print "course",  course,
                #print "date:",date
                lastDate = date
                x=y.join(valid)
                if x== 'A':
                    #gpsParams = {"date":date,"speed":speed,"course":course}
                    gpsParams.update({"date":date})
                    gpsParams.update({"speed":speed})
                    gpsParams.update({"course":course})
                    
                    speedml= float(speed)  * float(1.15)
                    #print speedml,
                    gpsParams.update({"speedml":speedml})
                    speedkm=float(speed)*float(1.82)
                    #print speedkm
                    gpsParams.update({"speedkm":speedkm})
                    
                    GPPMCdata = line
                    updateCount = updateCount+1
                    #print "count",     updateCount 
                    status = True
                    if gpsValidData:
                        if messageUpdate==True:
                            messageUpdate=False
                            errorHandle("Running")
                            newData = " date:" + str(date)+",time:"+ str(tim2)+" Running\n"#
                            updateCount=0

                            
                        if updateCount > 0:  #9:   
                            
                            newData = " date:" + str(date)+",time:"+ str(tim2) +", speed:"  + str(speed)  + "knots, course:"  +  str(course)  + newData  + "\n"
                            #print"================================================================="
                            #print newData
                            #dataFile.write(newData)
                            updateCount = 0
                            mqttGo =True
                            #newData=""
                        pass
        elif line.startswith( '$GPVTG' ) :
            if gpsOKflag == True:
                GPVTGdata=line 
                status = True
        else:
            pass
            """
$GPVTG         Track Made Good and Ground Speed.

eg1. $GPVTG,360.0,T,348.7,M,000.0,N,000.0,K*43
eg2. $GPVTG,054.7,T,034.4,M,005.5,N,010.2,K


           054.7,T      True track made good
           034.4,M      Magnetic track made good
           005.5,N      Ground speed, knots
           010.2,K      Ground speed, Kilometers per hour


eg3. $GPVTG,t,T,,,s.ss,N,s.ss,K*hh
1    = Track made good
2    = Fixed text 'T' indicates that track made good is relative to true north
3    = not used
4    = not used
5    = Speed over ground in knots
6    = Fixed text 'N' indicates that speed over ground in in knots
7    = Speed over ground in kilometers/hour
8    = Fixed text 'K' indicates that speed over ground is in kilometers/hour
9    = Checksum
The actual track made good and speed relative to the ground.

$--VTG,x.x,T,x.x,M,x.x,N,x.x,K
x.x,T = Track, degrees True 
x.x,M = Track, degrees Magnetic 
x.x,N = Speed, knots 
x.x,K = Speed, Km/hr
            """
         
    return status  



if os.name != "nt":
    import fcntl
    import struct
    def get_interface_ip(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', ifname[:15])
            )[20:24])


def get_lan_ip():
    ip = socket.gethostbyname(socket.gethostname())
    if ip.startswith("127.") and os.name != "nt":
        interfaces = ["eth0","eth1","eth2","wlan0","wlan1","wifi0","ath0","ath1","ppp0"]
        for ifname in interfaces:
            try:
                ip = get_interface_ip(ifname)
                break;
            except IOError:
                pass
    return ip



def waitForValidDate():
    global messageUpdate
    global lastDate
    
    result = False
    count =0
    messageUpdate = True 
    status = False
    
    while messageUpdate == True: 
        result=readData()
        if result ==True:  
            status = getGPdata()
            #print "status",status,
        count = count+1
        if count >3000:
            restartProg()
    
    return lastDate
    
#---------------------------------------------------------------------------    

def main(): 
    global gpsParams
    global lastDate
    global lastTime
    global errorLog
    global serin
    global logFile
    global updateCount
    global messageUpdate
    global dataFile
    global newData
    global mqttGo
    global GPGGAdata
    global GPVTGdata
    global GPPMCdata
    global gpsValidData
    global mqttl
 
    errorCount1=0
    errorCount2=0
    errorCount3=0
   
    dataCount=0
    lastDate=""
    lastTime=""
    gpsValidData=False
    rpi=False
    enableMQTT = False
    updateCount =0
    loop = True
        
    while loop == True:   
        try:
            print "Connecting... ", serialdevIn
            #connect to serial port
            serin = serial.Serial(serialdevIn, 4800)
            serin.flushInput()
            print serin.portstr  
            loop = False
        
        except:
            error =  "Failed to connect serial In"
            errorHandle(error)
            gpsOKflag =False
            time.sleep(5)    

    nowDate = waitForValidDate()
    #nowDate  =  time.strftime("%d%m%Y")
    if rpi==True:
        usbLocation = "//media//USBFLASH//"+nowDate+"//"
    else:
        usbLocation = "//media//hugh//USBFLASH//"+nowDate+"//"
    if not os.path.isdir(usbLocation):
        os.makedirs(usbLocation)
    fileName1 = usbLocation+"error.txt"
    fileName2 = usbLocation+"log.nmea"
    fileName3 = usbLocation+"data.txt"
    fileName4 = usbLocation+"map.nmea"

    
    print nowDate
    print fileName1
    

    GPGGAdata=""
    GPVTGdata=""
    GPPMCdata=""
    loopCount =0
    loopCountMax=1
    ipaddr = (get_lan_ip())
    print ipaddr
    print "version",version
    print "enableMQTT",enableMQTT
    print "RPI flag=",rpi
    print "Start"
    
    messageUpdate = True
    gpsOKflag =False
    lastTime =  "0000000.0"
    lastDate = "0"
    updateCount =5
    mqttGo=False
    mqttMessage = True
    try:
        mqttl = mosquitto.Mosquitto("gps")
        mqttl.on_connect = on_connect
        mqttl.on_publish = on_publish
        mqttl.connect(brokerLocal, port)
        localmosquitto=True
    except:
        print "no local mosquitto host\n"   
        localmosquitto=False
    try:
        bufsize = 0
        print "opening log file .. "
        

        print "Wait"
        time.sleep(3)
        
        errorLog = open(fileName1, 'a+', bufsize)
        logFile  = open(fileName2, 'a+' )
        dataFile = open(fileName3, 'a+')
        nmeaFile = open(fileName4, 'a+')

 
        dataFile.write("start gps logging\n")
        logFile.write("start gps logging\n")
    
    except:
        error = "Failed to open log file " 
        errorHandle(error)
        #unable to continue with no files open
        raise SystemExit

    error = "IP address "+ ipaddr 
    errorHandle(error)
    #dataFile.write(newData)
    if localmosquitto==False:
        error = "No local mosquitto sever " 
        errorHandle(error)
        

        
    try:
        print "Connecting... ", serialdevout
        #connect to serial port
        serout = serial.Serial(serialdevout, 4800)
        serout.flushOutput      #flushInput()
    
    except:
        error =  "Failed to connect serial Out\n"
        errorHandle(error)
        #cleanup()
    try:
        if enableMQTT==True:
            mqttc = mosquitto.Mosquitto("kelvinweb")
            #attach MQTT callbacks
            mqttc.on_connect = on_connect
            mqttc.on_publish = on_publish
            #connect to broker
            mqttc.connect(broker, port)
            error =  "mqtt connection made"
            errorHandle(error)
        else:
            error =  "mqtt NO remote connection made"
            errorHandle(error) 
        
    except:
        print "MQTT init error"
       
    messageUpdate = True
    while messageUpdate == True: 
        result=readData()
        if result ==True:  
            status = getGPdata()
        if messageUpdate == False: 
            nmeaFile.write(newData)
            logFile.write(newData)
            dataFile.write(newData)
            #print "newData",newData
            print"---------------------------------------------------------\n"
    try:    
        rc_count =0
        rc=0
        MQTT_RESET =60
        #Main Loop+++++++++++++++++++++++++++++++++
        while True: 
            try:
                if enableMQTT==True:
                    rc =mqttc.loop(0)
                pass
            except:
                rc_count=rc_count+1
                if rc_count > MQTT_RESET:
                    print "mqtt loop exception error",rc_count 
                    rc_count=0
                    pass
                rc=0
                pass
            
            result = readData()
    
            if result == True:
                #print "gpsData",gpsData
                logFile.write(gpsData)
                status = getGPdata()
                mqttl.publish(publishLocal3,gpsData)
                #print "==================================="
                #print GPGGAdata
                #print GPVTGdata
                #print "==================================="
                if status == True:
                    loopCount=loopCount+1
                    if loopCount>loopCountMax:
                        if localmosquitto==True:
                            mqttl.publish(publishLocal,GPGGAdata)
                            mqttl.publish(publishLocal,GPVTGdata)
                            mqttl.publish(publishLocal,GPPMCdata)
                            #mqttl.publish(publishLocal2,newData)
                            
                        nmeaFile.write(GPGGAdata)
                        nmeaFile.write(GPVTGdata)
                        nmeaFile.write(GPPMCdata)
                        #print "==================================="
                        loopCount=0
                else:
                    #errorCount1=errorCount1+1
                    #print "error count1",errorCount1,gpsData
                    #other messages
                    pass
            else:
                errorCount2=errorCount2+1
                #print "error count2",errorCount2,gpsData
            if rc==0:
                try:
                    if mqttGo==True:
                        if enableMQTT==True:
                            mqttc.publish(PublishAt,newData)
                        mqttl.publish(publishLocal2,newData)
                        #print"================================================================="
                        #print gpsParams.keys()
                        print "Date :",gpsParams["date"],"      Time:",gpsParams["time"],"\n"
                        print "\n"
                        print "Speed mph:",gpsParams["speedml"],"      kmh:",gpsParams["speedkm"],"\n"
                        print "\n"
                        print "lat :",gpsParams["north"],gpsParams["lat"],
                        print "long:",gpsParams["east"],gpsParams["lon"],"\n"
                        print "\n"
                        print "altitude",gpsParams["altitude"],"  sats",gpsParams["sats"],"  Course",gpsParams["course"],"\n"
                        print "\n"
                        dataCount=dataCount+1
                        if dataCount>9:
                            dataCount=0
                            #print newData
                            dataFile.write(newData)
                        mqttGo=False
                        mqttMessage=True
                    pass
                except:
                    print "------------------------------"
            else:
                rcn=str(rc)
                if mqttMessage==True:
                    error =  "MQTT Connection Problem  " + rcn 
                    errorHandle(error)
                    mqttMessage=False
                rc_count=rc_count+1
                if rc_count > MQTT_RESET:
                    #print "rc count:",rc_count 
                    if enableMQTT==True:
                        mqttc.disconnect()
                    if rc_count>MQTT_RESET+1:    
                        try:
                            if enableMQTT==True:
                                mqttc.connect(broker, port, 60, True)
                                error =  "MQTT Re-connection " 
                                errorHandle(error)
                        except:
                            #print "connection problems"  #goes here if no internet connection
                            pass
                        rc_count=0
                rc=0
                pass
    
     
    # handle list index error (i.e. assume no data received)
    except (IndexError):
        error =  "No data received within serial timeout period\n"
        errorHandle(error)
        cleanup()
    # handle app closure
    except (KeyboardInterrupt):
        print "Interrupt received"
        error =  "No data received within serial timeout period\n"
        errorHandle(error)
        cleanup()
    except (RuntimeError):
        error =   "uh-oh! time to die\n"
        errorHandle(error)
        cleanup()
        pass 

    
if __name__ == "__main__":
    main()    
    
    
    
    
