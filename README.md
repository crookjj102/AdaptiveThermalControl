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

Here are comparisons against a well-tuned (at 100 deg) PID with integral clamping vs this algorithm:
100 deg setpoint:

<img width="577" height="451" alt="image" src="https://github.com/user-attachments/assets/e8e8c8c3-f6a2-4f45-81d0-032cb9bbf3a0" />


The PID and Adaptive performance are similar in the PID's tuned range, with only a few seconds' difference in settling time and little to no overshoot (both within a degree or so). 

300 deg setpoint:
<img width="577" height="451" alt="image" src="https://github.com/user-attachments/assets/d2324a6d-571e-442f-937e-7e009f16f3bc" />

At 300 degrees, this changes, with the PID wildly overshooting (27 degrees!) despite the same parameters. The settling time of the adaptive controller remains quite good. 

Now, in both of these, you can see the initial slug of energy being applied, then the controller learning the system and heading for the setpoint. The initial shot after tuning is intentionally conservative; it doesn't matter. It still tends to be equivalent or better performance, even with no starting knowledge of the system and a deliberately absurd first estimate. Only in the exact tuned range for the PID does this algorithm show any appreciable lack of performance. That's ok, the span of setpoints for which it will retain performance is wide. 

The tradeoff for this algorithm is that for applications in which there is little power overhead available (i.e. the heat losses are nearly equivalent to available power), it inherently cannot reach as high of a temperature. This is fundamental to the way that the controller functions and would not be resolvable without introducing a different control scheme toward the upper end of the power duty. 
