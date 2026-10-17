class Heater():
    def __init__(self, powerCapacity):
        self.powerCapacity = powerCapacity
        self.heaterIsOn = False
        self.powerLevel = 0
        


    def heaterOn(self, powerLevel_Percent):
        if(powerLevel_Percent>0):
            self.powerLevel = powerLevel_Percent
            self.heaterIsOn = True
            return True
        else:
            return self.heaterOff()
        
    
    
    def heaterOff(self):
        #turns off heater. Returns 0. 
        self.heaterIsOn = False
        self.powerLevel = 0
        return False

    def getEnergyContributed(self, dt):
        return float(self.powerLevel * dt * self.powerCapacity / 100.0)

    def getPowerCapacity(self):
        return self.powerCapacity

    def getResponseTime(self):
        return self.responseTime