import stepper
from threading import Timer

UP = stepper.CCW
DOWN = stepper.CW


class LinearController():
    def __init__(self, motor:stepper.StepperMotor, screw_pitch:float):
        self._motor = motor
        self._screw_pitch = screw_pitch
        self.is_running = False
        self._running_timer = None

    def _get_interval_from_distance(self, speed:float, distance:float, is_linear:bool=True):
        '''
        Compute the required time interval to travel to the
        specified distance, given a desired speed.

        Parameters
        ----------
        speed : float
            The desired speed for the motion. It can be
            specified either in mm/s (linear) and
            RPS (rotational). Default is linear.
        distance : float
            The linear distance to travel to, expressed in mm.
        is_linear : bool, default=True
            If True the speed is to be given in mm/s (linear),
            if False the speed is expected to be in RPS (rotational).

        Return
        ------
        interval : float
            The computed time interval to travel the given
            distance at the desired speed, given in seconds.
        '''
        if is_linear:
            interval = distance/speed
        else:
            interval = distance/self._get_linear_speed(speed)

        return interval

    def _get_rotational_speed(self, linear_speed:float):
        '''
        Convert a specified linear speed into the equivalent
        rotational speed.

        Parameters
        ----------
        linear_speed : float
            The specified linear speed expressed in mm/s.

        Return
        ------
        rotational_speed : float
            A rotational speed equivalent to the given linear speed
            expressed in RPS (revolutions-per-second).
        '''
        rotational_speed = linear_speed / self._screw_pitch
        return rotational_speed

    def _get_linear_speed(self, rotational_speed:float):
        '''
        Convert a specified rotational speed into the equivalent
        linear speed.

        Parameters
        ----------
        rotational_speed : float
            The specified rotational speed expressed in RPS (revolutions-per-second).

        Return
        ------
        rotational_speed : float
            A linear speed equivalent to the given rotational speed
            expressed in mm/s.
        '''
        linear_speed = rotational_speed * self._screw_pitch
        return linear_speed
    
    def abort(self):
        if self.is_running:
            print('Aborted')
            self._running_timer.cancel()
            run_time, run_distance = self._stop()
        else:
            run_time = None
            run_distance = None

        return run_time, run_distance
    
    def run(self, speed:float, distance:float, direction:bool, is_linear:bool=True):  
        if not self.is_running:
            # Compute the run time interval
            interval = self._get_interval_from_distance(speed, distance, is_linear)
            
            # Init the timer
            self._running_timer = Timer(interval, self._stop)

            # Get the rotational speed, if necessary
            if is_linear:
                speed = self._get_rotational_speed(speed)
            
            print(f'Run for {interval} s at {speed} rps')

            # Start the motor
            self._motor.start(speed, direction)

            # Start the timer
            self._running_timer.start()

            # Switch on is_running flag
            self.is_running = True
        else:
            print('The motor is already running')
            interval = None
        
        return interval

    def run_to(self):
        # run to a specified absolute point
        return
    
    def _stop(self):
        # Stop the motor
        run_time = self._motor.stop()
        run_distance = self._get_distance_from_interval(self._rotational_speed, run_time, False)

        # Delete running timer
        self._running_timer = None

        return run_time, run_distance
