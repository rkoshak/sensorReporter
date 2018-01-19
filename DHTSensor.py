"""
   Copyright 2016 Richard Koshak

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

 Script: DHTSensor.py
 Author: Martin S. Eskildsen / Rich Koshak
 Date:   October 20, 2017
 Purpose: Checks the state of the GPIO pin and publishes any changes to humidity and/or temperature


TODO: Allow other DHT sensors than the DHT22

"""


import sys
import time
import Adafruit_DHT
import ConfigParser

class DHTSensor:
    """Represents a DHT sensor connected to a GPIO pin"""


    def __init__(self, connections, logger, params, sensors, actuators):
        """Sets the sensor pin to pud and publishes its current value"""

        self.lastpoll = time.time()

        #Initialise to some time ago (make sure it publishes)
        self.lastPublish = time.time() - 1000

        self.logger = logger
        self.sensorType = params("Sensor")
        self.sensorMode = params("Mode")

        self.sensor = Adafruit_DHT.DHT22
        self.pin = int(params("Pin"))

        self.precissionTemp = int(params("PressionTemp"))
        self.precissionHum = int(params("PressionHum"))
        self.useF = False

        try:
            if (params("Scale") == 'F'):
                self.useF = True
        except ConfigParser.NoOptionError:
            pass

        #Use 1 reading as default
        self.ARRAY_SIZE = 1

        if (self.sensorMode == "Advanced"):
            #Array size of last readings
            self.ARRAY_SIZE = 5

        #Initialize Array
        self.arrHumidity = [None] * self.ARRAY_SIZE
        self.arrTemperature = [None] * self.ARRAY_SIZE

        self.humidity = None
        self.temperature = None

        self.forcePublishInterval = 60

        self.destination = params("Destination")
        self.poll = float(params("Poll"))

        self.publish = connections

        self.logger.info("----------Configuring DHT Sensor: Type='{0}' pin='{1}' poll='{2}' destination='{3}' Initial values: Hum='{4}' Temp='{5}'".format(self.sensorType, self.pin, self.poll,  self.destination, self.humidity, self.temperature))

        self.publishState()
    

    def convertTemp(self, value):
        return value if self.useF == False else value * 9 / 5.0 + 32


    def checkState(self):
        """Detects and publishes any state change"""

        hasChanged = False
        valueHum, valueTemp = self.readSensor()

        if ((valueHum is None) or (valueTemp is None)):
            self.logger.warn("Last reading isn't valid. preserving old reading T='{0}', H='{1}'".format(self.temperature, self.humidity))
            return  

        #Verify reading of humidity
        if(valueHum != self.humidity):
            self.logger.info("Humidity changed from '{0}' to '{1}'".format(self.humidity, valueHum))

            self.humidity = valueHum
            hasChanged = True


        #Verify reading of temperature
        if(valueTemp != self.temperature):
            self.temperature = valueTemp
            hasChanged = True


        if (hasChanged or (time.time() - self.lastPublish)>self.forcePublishInterval):
            self.publishState()

    def publishStateImpl(self, data, destination):
        for conn in self.publish:
            conn.publish(data, destination)

    def publishState(self):
        """Publishes the current state"""
        didPublish = False

        if (self.humidity is not None):
            didPublish = True
            strHum = str(round(self.humidity,self.precissionHum))
            self.logger.debug("Publish humidity '{0}' to '{1}'".format(strHum, self.destination + "/humidity"))
            self.publishStateImpl(strHum, self.destination + "/humidity")

        if (self.temperature is not None):
            didPublish = True
            strTemp = str(round(self.temperature, self.precissionTemp))
            self.logger.debug("Publish temperature '{0}' to '{1}'".format(strTemp, self.destination + "/temperature"))
            self.publishStateImpl(strTemp, self.destination + "/temperature")

        if (didPublish):
            self.lastPublish = time.time()


    def isReadingValid(self, value, acceptableMin, acceptableMax):
        if (value is None):
            return False

        if ((value >= acceptableMin) and (value <= acceptableMax)):
            return True
        
        return False


    def readSensor(self):

        resultHum = None
        resultTemp = None

        valueHum, valueTemp = Adafruit_DHT.read_retry(self.sensor, self.pin, 2)
        #print("Raw reading H:{0} T:{1}".format(valueHum, valueTemp ))

        # Is humidity and temperature reading valid?
        if ((self.isReadingValid(valueHum, 0.0, 100.0)) and (self.isReadingValid(valueTemp, -40.0, 125.0))):
            self.arrHumidity.append(round(valueHum, 2))
            valueTemp = self.convertTemp(valueTemp);
            self.arrTemperature.append(round(valueTemp, 2))
        else:
            #Reading out of bounds
            return resultHum, resultTemp
    
        if (len(self.arrHumidity)>self.ARRAY_SIZE):
            del self.arrHumidity[0]

        if (len(self.arrTemperature)>self.ARRAY_SIZE):
            del self.arrTemperature[0]

        if (self.sensorMode == "Advanced"):
            sumHum = sum(filter(None, self.arrHumidity))
            noHumReadings = len(filter(None, self.arrHumidity))
            if (noHumReadings>0):
                resultHum = float(str(round(sumHum/noHumReadings, self.precissionHum)))

            sumTemp = sum(filter(None, self.arrTemperature))
            noTempReadings = len(filter(None, self.arrTemperature))
        
            if (noTempReadings>0):
                resultTemp = float(str(round(sumTemp/noTempReadings, self.precissionTemp)))

            #print("readValueAdvanced: Result - Hum:'{0}', Temp:'{1}'".format(resultHum, resultTemp))
            self.logger.info("readValue: Hum:'{0}', Temp:'{1}'".format(resultHum, resultTemp))

        #Simple mode -> Just return last reading
        else:
            resultHum =  float(str(round(valueHum, self.precissionHum)))
            resultTemp = float(str(round(valueTemp, self.precissionTemp)))

            self.logger.info("readValue: Hum:'{0}', Temp:'{1}'".format(resultHum, resultTemp))

            #print("readValueSimple: Result - Hum:'{0}', Temp:'{1}'".format(resultHum, resultTemp))

        return resultHum, resultTemp
