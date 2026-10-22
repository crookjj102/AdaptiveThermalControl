'''
Adaptive thermal controller inspired by orbital mechanics.

It is a 4-state FSM that controls the temperature of a zone in an injection molding machine. The states are:

1. **Calculate Energy**: The controller calculates the amount of energy required to reach SP and converts to burn time. 
2. **Burn**: The controller burns the heater at the set power maximum until burn time is reached.
3. **Coast**: The controller coasts until the peak temperature is detected and the system starts moving back down
4. **Adapt**: The controller computes the delta between SP and the peak and recalculates the calorimetry estimate 
                based on this delta.

The burn time calculation can be simplified from:

Q = P * t_burn = C * m * deltaT
to:
t_burn = K * deltaT
because the heater power and the thermal mass can be considered constant.

tuning can be achieved with this controller by setting t_burn to a constant time and measuring the response, 
although tuning is not strictly necessary if the controller starts with a safe estimate of the system. 

This particular system uses a safe temperature and restricts power output until that safe temperature is achieved. 
This is due to the habit of micah heaters trapping moisture and popping holes in the elements when too much power 
is applied too quickly. 
'''

import asyncio
from Heater import Heater
from Zone import improvedZone

class AdaptiveController():
    def __init__(self, zone, SP, maxPower, precision= 0.1, tuneTime = 0.2, safe_temp =300, safe_percent=30):
        self.zone = zone
        self.targetTemperature = SP  # Setpoint temperature  
        self.burnTime = 0.0  # Time to burn the heater
        self.loopPrecision = precision
        self.maxPower = maxPower
        self.burnTime = 0
        self.state = ''
        self.prevPeak = 0
        self.untuned = True
        self.crossedSafety = False
        self.safeTemp = safe_temp
        self.tuneTime = tuneTime
        self.safePercent = safe_percent
        self.currentTemperature = self.zone.currentTemperature # Current temperature of the zone
        self.Kp = 0 # Proportional parameter
        self.Ki = 0 # Integral paramete
        self.K = 0 # Tuning parameter
        
    
    def determineIfCrossed(self): # determines if we've crossed the steam danger zone on the heater. 
        if self.prevPeak<self.safeTemp and self.currentTemperature>self.safeTemp and not self.crossedSafety:
            self.crossedSafety = True
            return True
        else:
            return False

    def calculateBurnTime(self):
        if self.untuned:
            self.prevPeak = self.currentTemperature
            self.burnTime = self.tuneTime
            
        else:
            if self.currentTemperature<self.safeTemp:
                deltaT = self.safeTemp - self.currentTemperature    
            else:
                deltaT = self.targetTemperature - self.currentTemperature
            self.burnTime = self.K * deltaT
        

    
    async def burn(self):
        self.zone.heaterOn(self.maxPower)  # Set the heater power to maximum
        ttb = self.burnTime
        await asyncio.sleep(ttb)
        self.zone.heaterOff() # Turn off the heater
    
    async def coastToPeak(self, precision):
        lastTemperature = self.currentTemperature-1
        currentTemperature = self.currentTemperature
        waiting = True
        count = 0
        while(waiting):
            await asyncio.sleep(precision)
            currentTemperature = self.currentTemperature
            if(self.targetTemperature-currentTemperature>50):
                waiting = float(currentTemperature - lastTemperature)/precision >= 0.1 # far from setpoint we let it be sloppy in the measurement
            else:
                waiting = float(currentTemperature - lastTemperature)/precision >= 0.01
            count += 1
            lastTemperature = currentTemperature
        return currentTemperature
            #print(self.zone.currentTemperature, (currentTemperature-lastTemperature)/precision, self.burnTime)
        return currentTemperature
    
    def updateSystemEstimate(self, peakTemperature): 
        if not self.untuned:    
            if self.prevPeak<self.safeTemp and not self.untuned:
                tempError = self.safeTemp - peakTemperature
                errorPercent =  float(tempError/self.safeTemp) 
            else:
                tempError = self.targetTemperature - peakTemperature
                errorPercent =  float(tempError/self.targetTemperature)   
            self.K *= float(1.0 + errorPercent)
            if self.determineIfCrossed():
                self.K *= self.safePercent/self.maxPower
        else:
            self.untuned =False
            self.K = 0.8*(self.burnTime/(peakTemperature-self.prevPeak))#intentionally conservative first shot
        self.prevPeak = peakTemperature
        #print(self.K)

    async def runTemperature(self):
        tempFilter = MovingAverageArray(500)
        while True:
            await asyncio.sleep(self.loopPrecision)
            tempFilter.insert(self.zone.calculateCurrentTemperature(self.loopPrecision))
            self.currentTemperature = tempFilter.average()


    async def printStatus(self):
        while(True):
            await asyncio.sleep(1)
            print("Current Temperature: ", self.currentTemperature)
            print("Heater power level: ", self.zone.heater.powerLevel)
            print("heater on?: ", self.zone.heater.heaterIsOn)
            print("burnTime: ", self.burnTime)
            print("K: ", self.K)
            print("State: ", self.state)

    async def runController(self):
        while True:
            if(self.untuned):
                self.state = "Tuning..."
            if not self.untuned:
                self.state = 'Calculating...'
            self.calculateBurnTime()
            if not self.untuned:
                self.state = 'Burning...'
            await self.burn()
            if not self.untuned:
                self.state = 'Coasting...'
            peakTemperature = await self.coastToPeak(self.loopPrecision)
            self.state = 'Altering estimate...'
            self.updateSystemEstimate(peakTemperature)

            await asyncio.sleep(self.loopPrecision)
            

    
    async def run(self):
        await asyncio.gather(
            self.runTemperature(), 
            self.runController()
            #self.printStatus()
            
            )
'''
An array that stores its own sum for O(1) rolling averaging. 

This was a method for filtering sensor readings, as I was injecting noise into the sensor readings to test the response. 
Obviously, for demoing the controller, it's best to show what happens when it gets clean data, as normally things are electrically filtered. 
'''

class MovingAverageArray:
    def __init__(self, length):
        self.length = length
        self.index = 0
        self.array = []
        self.sum = 0
    def insert(self, element):
        if len(self.array)<self.length:
            self.array.append(element)
            self.sum+= element
        else:
            self.sum-=self.array[self.index]
            self.sum+=element
            self.array[self.index] = element
        self.index+=1
        if self.index>=self.length:
            self.index=0
    def average(self):
        if len(self.array)<self.length:
            return self.sum/len(self.array)
        else:
            return self.sum/self.length
    

    
