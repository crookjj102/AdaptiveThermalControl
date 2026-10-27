# AdaptiveThermalControl
This is an algorithm that was originally implemented in Ladder Logic for thermal control of injection molding press barrels. 

The issue with the typical PID implementation of thermal control in this specific application is the following:
1. There is significant thermal lag in the system, so continuous addition of energy to compensate for current error will either ring and cause unwanted temperature oscillations, or requires a rather large differential coefficient, which causes sensitivity to noise and a long settling time. 
2. The range of setpoints on any given system in the original case was between 200 and 700 degrees F, and this meant that static tuning on a standard PID would be invalid at some point in the range, forcing a compromise that would produce both inaccurate and slow performance. 
3. The temperature accuracy needed to be tighter than +/-7 deg f to prevent degradation of the polymer chains. 

Coming to this conclusion, I devised a new method of thermal control, which was based on Hohmann maneuvers for orbital adjustment. In orbital mechanics, neither altitude nor velocity is the target, energy is the target. Therefore, we could develop thermal control that tracks energy addition into the system using P x t_burn = C x m_thermal x deltaT, where P is heater power, t_burn is the "maneuver" burn time, C is the calorimetry constant for the system, m_thermal is the thermal mass, and deltaT is the difference between Present Value (PV) and SetPoint (SP). 

We may simplify this, using some assumptions. We can assume that the system power is relatively constant, that the thermal mass and calorimetry are roughly so as well, and this yields our control law:

t_burn = k x deltaT

Which appears to be proportional control until we realize that we aren't adjusting power percentage, we're adjusting total energetic input. 

So the controller functions as a finite state machine with four states:
1. Estimate t_burn from what we know about the system.
2. Turn the heater on for t_burn seconds. 
3. Turn the heater off and wait until the temperature peaks.
4. Measure the peak, and calculate the difference between the temperature change we expected and what actually happened, and recalculate k to make the next burn more accurate. 

Now this specific implementation has some interesting modifications. The original used an offline tune, in which a test slug of energy was sent to the system, and the response was measured, giving an initial value for k, and the runtime learning was restricted to within a reasonable boundary. 
We're just using a simulated plant here, so this system starts by sending the test slug every startup, and it will predict where peaks roughly should occur once the derivative settles if it's far from SP, dramatically decreasing the settling time. 

The real implementation exhibited exceptional stability across the setpoint range, exceptional accuracy compared to the PID alternatives, and a trivial setup time. This method of control also exhibited nearly perfect control when artificial disturbances were added, and this became the default method of thermal control for that facility. 

The PID and Adaptive performance are similar in the PID's tuned range, with only a few seconds' difference in settling time and little to no overshoot (both within a degree or so). 

300 deg setpoint, PID has clamping:

<img width="625" height="479" alt="image" src="https://github.com/user-attachments/assets/9cb79332-4204-4f86-95b1-70b4924f8f64" />

300 deg setpoint, adaptive has prior knowledge of the system:

<img width="625" height="479" alt="image" src="https://github.com/user-attachments/assets/74bee96a-276c-4571-9974-2b1edb144df4" />


Now, in this example, you can see the initial slug of energy being applied, then the controller learning the system and heading for the setpoint. The initial shot after tuning is intentionally conservative; it doesn't matter. It still tends to be equivalent or better performance, even with no starting knowledge of the system and a deliberately absurd first estimate. Only in the exact tuned range for the PID does this algorithm show any appreciable lack of performance. That's ok, the span of setpoints for which it will retain performance is wide. Even with no initial understanding of the system, and the PID possessing anti-windup, the adaptive beats PID to the setpoint and maintains a much higher degree of accuracy. 

The tradeoff for this algorithm is that for applications in which there is little power overhead available (i.e. the heat losses are nearly equivalent to available power), it inherently cannot reach as high of a temperature. This is fundamental to the way that the controller functions and would not be resolvable without introducing a different control scheme toward the upper end of the power duty. 

Now, one of the biggest advantages to this approach was the fact that heater bands on the presses could have more degradation and still be useful. Below is a graph of both PID and adaptive controllers when the heater degrades by one watt per simulation tick: 

<img width="784" height="547" alt="image" src="https://github.com/user-attachments/assets/8ad104d7-bc4a-4151-85bc-60b6ecd0b195" />


As you can see, the PID loses control authority more rapidly, and the adaptive controller maintains control for longer before also losing control of the situation. Noise is due to the exceptionally high time dilation used (it's rather slow and I'm rather impatient). Note that integral clamping was disabled for the PID in this test to help it succeed. 

