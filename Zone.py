# this is a class that simulates a heater zone in an injection molding machine. 

import Heater
import asyncio
import math
import random

class Zone():
    def __init__(self, heater, ambientTemp, mass, calorimetryConst, diameter, length, timeDilation):
        self.heater = heater
        self.ambientTemp = ambientTemp
        self.mass = mass
        self.calorimetryConst = calorimetryConst
        self.currentTemperature = ambientTemp
        self.diameter = diameter
        self.length = length
        self.totalEnergy = 0
        self.conductiveHeatLossRate = 0
        self.timeDilation = timeDilation

        self.surfaceArea = self.diameter * self.length*math.pi

        # Physical constants
        self.g = 9.81                              # Gravity (m/s^2)
        self.emissivity = 0.80                     # Rough estimate for oxidized steel/heater bands
        self.sigma = 5.670374e-8                   # Stefan-Boltzmann constant (W/m^2*K^4)

    
    
    def calculateHTCoeff(self):
        # used for Newton's law of cooling; 
        #h = q/deltaT
        # Convert to Kelvin for absolute thermodynamic equations
        T_s = self.currentTemperature + 273.15
        T_inf = self.ambientTemp + 273.15
        
        deltaT = T_s - T_inf
        if deltaT <= 0.01:
            return 0.0  # Prevent division by zero if it's perfectly at ambient

        #Evaluate properties at Film Temperature
        T_film = (T_s + T_inf) / 2.0
        # Thermal conductivity (k) of air: approx fit
        k = 0.02425 + 7.47e-5 * (T_film - 273.15)
        # Kinematic viscosity (nu) of air: approx fit
        nu = (1.33e-5 + 9.34e-8 * (T_film - 273.15))
        # Prandtl number for air is relatively stable around 0.7
        Pr = 0.707
        # Volumetric expansion coefficient for ideal gas
        beta = 1.0 / T_film

        #Calculate Rayleigh Number
        # Ra_D = (g * beta * deltaT * D^3) / nu^2 * Pr
        Ra_D = (self.g * beta * deltaT * (self.diameter ** 3)) / (nu ** 2) * Pr
        # Safeguard against zero or negative Rayleigh numbers
        Ra_D = max(Ra_D, 1e-5)

        num = 0.387 * (Ra_D ** (1.0 / 6.0))
        den = (1.0 + (0.559 / Pr) ** (9.0 / 16.0)) ** (8.0 / 27.0)
        Nu_D = (0.60 + (num / den)) ** 2

        h_conv = (Nu_D * k) / self.diameter

        h_rad = self.emissivity * self.sigma * (T_s**2 + T_inf**2) * (T_s + T_inf)

        return h_conv + h_rad


    def calculateHeatLoss(self, dt):
        h_total = self.calculateHTCoeff()
        deltaT = self.currentTemperature - self.ambientTemp
        return h_total*self.surfaceArea*deltaT*dt
    
    def conductiveHeatLoss(self, lossRate):
        self.conductiveHeatLossRate = lossRate

    def calculateHeatGain(self, dt):
        #if self.heater.heaterIsOn:
        energyContributed = self.heater.getEnergyContributed(dt)
        return energyContributed
        #else:
        #    return 0

    def calculateCurrentTemperature(self, dt):
        self.currentTemperature += (self.calculateHeatGain(dt*self.timeDilation)-self.calculateHeatLoss(dt*self.timeDilation)-self.conductiveHeatLossRate*dt*self.timeDilation)/(self.mass*self.calorimetryConst)
        return self.currentTemperature

class improvedZone():
    def __init__(self, heater, ambientTemp, mass, calorimetryConst, diameter, length, safetytemp, safetyPercent, timeDilation):
        self.heater = heater
        self.ambientTemp = ambientTemp
        self.mass = mass
        self.calorimetryConst = calorimetryConst
        self.currentTemperature = ambientTemp
        self.diameter = diameter
        self.length = length
        self.totalEnergy = 0
        self.heaterZone = Zone(heater, ambientTemp, mass/2, calorimetryConst, diameter, length/2, timeDilation)
        self.maxflux = heater.powerCapacity
        self.heatProxy = Heater.Heater(self.maxflux)
        self.sensorZone = Zone(self.heatProxy, ambientTemp, mass/2, calorimetryConst, diameter, length/2, timeDilation)
        self.area = 0.25*3.14159*self.diameter**2
        self.thermalConductivity = 31
        self.safetyPercent = safetyPercent
        self.safetytemp = safetytemp
        self.timeDilation = timeDilation

    def heaterOn(self, power):
        #micah heater bands require low power below 300 to prevent popping holes in them from steam pockets.
        if(self.sensorZone.currentTemperature<self.safetytemp):
            self.heaterZone.heater.heaterOn(self.safetyPercent)
        else:
            self.heaterZone.heater.heaterOn(power)

    def heaterOff(self):
        self.heaterZone.heater.heaterOff()
        
    def setSensorZonePower(self):
        tempDiff = self.heaterZone.currentTemperature - self.sensorZone.currentTemperature
        if tempDiff > 0:
            flux = tempDiff*self.area*self.thermalConductivity/self.length
            self.heaterZone.conductiveHeatLoss(flux)
            self.heatProxy.heaterOn(100.0*flux/self.maxflux)
        elif tempDiff < 0:
            flux = -tempDiff*self.area*self.thermalConductivity/self.length
            self.heaterZone.conductiveHeatLoss(flux)
        else:
            self.sensorZone.powerLevel = 0.0
            self.heaterZone.conductiveHeatLoss(0)
        
        
    def calculateCurrentTemperature(self, dt):
        self.setSensorZonePower()
        self.sensorZone.calculateCurrentTemperature(dt)
        self.heaterZone.calculateCurrentTemperature(dt)
        self.currentTemperature = self.sensorZone.currentTemperature
        #noiseqty = self.currentTemperature*0.01
        #noise = random.uniform(-noiseqty, noiseqty)
        return self.sensorZone.currentTemperature #+noise