import asyncio
from AdaptiveController import AdaptiveController
from PID import PID
from Zone import improvedZone as Zone
from Heater import Heater
import matplotlib.pyplot as plt
import numpy as np
import time

fig, ax = plt.subplots()
plt.ion()

async def update_graph(x_values, y1_values, y2_values):
    while True:
        ax.clear()

        ax.plot(x_values[-1000000:], y1_values[-1000000:], label="PID")
        ax.plot(x_values[-1000000:], y2_values[-1000000:], label="Adaptive")

        ax.set_title("Temperature")
        ax.set_xlabel("Time")
        ax.set_ylabel("Temperature")
        ax.legend()

        plt.pause(0.01)
        await asyncio.sleep(0.09)

async def monitorZones(zone1, zone2, temps1, temps2, times, currTime, timeDilation):
    while(True):
        await asyncio.sleep(.1)
        temp1 = "%3.2f" % zone1.currentTemperature
        temp2 = "%3.2f" % zone2.currentTemperature
        times.append(currTime*timeDilation)
        currTime += .1
        temps1.append(zone1.currentTemperature)
        temps2.append(zone2.currentTemperature)
 
        print("Zone1 Temperature: ", temp1, "Zone 1 Power: ", int(zone1.heaterZone.heater.powerLevel), "Zone2 Temperature: ", temp2, "Zone 2 Power: ", int(zone2.heaterZone.heater.powerLevel))


async def main():
    power = 2500.0
    ambient = 35.0
    mass = 15
    calorimetryConst = 36.0
    diameter = 0.2
    length = 0.09 
    setpoint = 300.0
    maxPower = 100

    safetytemp = 00
    safetyPercent = 40
    timeDilation = 10.0

    tuneTime = 3
 
    #create PID controlled zone
    PIDHeater = Heater(power)
    PIDZone = Zone(PIDHeater, ambient, mass, calorimetryConst,diameter,length, safetytemp, safetyPercent, timeDilation)
    PIDController = PID(PIDZone, setpoint, maxPower, 3, 1, 40, 0.01, True, 20, timeDilation)#tuned to 100 C 

    adaptiveHeater = Heater(power)
    adaptiveZone = Zone(adaptiveHeater, ambient, mass, calorimetryConst,diameter,length, safetytemp, safetyPercent, timeDilation)
    adaptiveController = AdaptiveController(adaptiveZone, setpoint, maxPower,0.01, tuneTime, safetytemp, safetyPercent, timeDilation)

    # create graph
    x_values = []
    y_pid = []
    y_adaptive = []
    currTime = 0 
    
    start_time = time.time()


    await asyncio.gather(
        adaptiveController.run(), 
        PIDController.run(), 
       monitorZones(PIDZone, adaptiveZone, y_pid,y_adaptive, x_values, currTime, timeDilation),
        update_graph(x_values, y_pid, y_adaptive)
   )
        

asyncio.run(main())
