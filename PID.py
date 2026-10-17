import asyncio
from Heater import Heater
from Zone import improvedZone

class PID():
    def __init__(self, zone, SP, maxPower, Kp=0.1, Ki=0.0, Kd=0.0, precision=0.1, hasClamping = True, clampPercent = 30):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_error = 0
        self.integral = 0
        self.zone = zone
        self.SP = SP
        self.maxPower = maxPower
        self.loopPrecision = precision
        self.currentTemperature = self.zone.currentTemperature
        self.hasClamping = hasClamping
        self.clampPercent = clampPercent

    def getError(self, temp):
        return float(self.SP-self.currentTemperature)
    
    def proportionalTerm(self, error):
        return float(self.Kp * error)

    def derivativeTerm(self, error, prev_error):
        return float(-self.Kd * (prev_error-error)/self.loopPrecision)

    def integralTerm(self, error):
        self.integral += error*self.loopPrecision
        #clamp integral term to prevent windup
        integralTerm = float(self.Ki * self.integral*self.loopPrecision)
        
        if integralTerm>=self.maxPower*self.clampPercent and self.hasClamping:
            integralTerm = self.maxPower/(self.clampPercent)
        return integralTerm

    def output(self, powerLevel):
        if powerLevel > self.maxPower:
            powerLevel = self.maxPower
            self.zone.heaterOn(powerLevel)
        elif powerLevel < 0:
            powerLevel = 0
            self.zone.heaterOff()
        else:
            self.zone.heaterOn(powerLevel)

    async def runTemperature(self):
        while True:
            await asyncio.sleep(self.loopPrecision)
            self.currentTemperature = self.zone.calculateCurrentTemperature(self.loopPrecision)
        
    async def runController(self):
        error = self.getError(self.currentTemperature)
        while True:
            self.prev_error = error
            error = self.getError(self.currentTemperature)
            proportionalTerm = self.proportionalTerm(error)
            derivativeTerm = self.derivativeTerm(error, self.prev_error)
            integralTerm = self.integralTerm(error)
            output = proportionalTerm + derivativeTerm + integralTerm
            self.output(output)
            await asyncio.sleep(self.loopPrecision)

    async def run(self):
        await asyncio.gather(
            self.runTemperature(), 
            self.runController())
