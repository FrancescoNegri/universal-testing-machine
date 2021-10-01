import controller.stepper as stepper
from threading import Timer
from gpiozero import Button

UP = stepper.CW
DOWN = stepper.CCW

class LinearController():
    '''
    Class controlling a stepper motor (rotational) from a linear point of view.
    '''
    def __init__(self, motor:stepper.StepperMotor, screw_pitch:float, pin_end_up:int, pin_end_down:int):
        '''
        Parameters
        ----------
        motor : StepperMotor
            The stepper motor to control.
        screw_pitch : float
            The pitch of the screw employed to convert the rotational
            motion of the motor to a linear one, specified in mm.
        '''
        self._motor = motor
        self._screw_pitch = screw_pitch

        # Calibration & Position attributes
        self.is_calibrated = False
        self.absolute_position = None
        self._calibration_direction = None

        # Running attributes
        self.is_running = False
        self._running_direction = None
        self._running_timer = None
        self._rotational_speed = None     

        # Other
        self._endstop_up = Button(pin_end_up)
        self._endstop_down = Button(pin_end_down)   

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
        if distance is not None:
            if is_linear:
                interval = distance/speed
            else:
                interval = distance/self._get_linear_speed(speed)
        else:
            interval = None

        return interval

    def _get_distance_from_interval(self, speed:float, interval:float, is_linear:bool=True):
        '''
        Compute the travelled distance for a specified
        time interval, given a desired speed.

        Parameters
        ----------
        speed : float
            The desired speed for the motion. It can be
            specified either in mm/s (linear) and
            RPS (rotational). Default is linear.
        interval : float
            The specified time interval, expressed in seconds.
        is_linear : bool, default=True
            If True the speed is to be given in mm/s (linear),
            if False the speed is expected to be in RPS (rotational).

        Return
        ------
        distance : float
            The computed travelled distance in the specified
            time interval considering the desired speed, given
            in mm.
        '''
        if interval is not None:
            if is_linear:
                distance = interval * speed
            else:
                distance = interval * self._get_linear_speed(speed)
        else:
            distance = None

        return distance

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
    
    def _reset_running_attributes(self):
        '''
        Reset the running attributes to their default
        values after each run.
        '''
        self.is_running = False
        self._running_direction = None
        self._running_timer = None
        self._rotational_speed = None

        return

    def _stop(self):
        '''
        Stop the running motor.

        Returns
        -------
        run_interval : float
            The time interval the motor has been running for,
            given in seconds.
        run_distance : float
            The distance travelled by the motor,
            given in mm.
        '''
        if self.is_running:
            # Stop the motor
            run_interval = self._motor.stop()
            run_distance = self._get_distance_from_interval(self._rotational_speed, run_interval, is_linear=False)

            if self.is_calibrated:
                self._update_absolute_position(run_distance)

            # Reset running attributes
            self._reset_running_attributes()
        else:
            run_interval = None
            run_distance = None

        return run_interval, run_distance
    
    def _update_absolute_position(self, run_distance:float):
        # if self._running_direction.get_value() == UP.get_value():
        #     if self._calibration_direction.get_value() == UP.get_value():
        #         self.absolute_position -= run_distance

        #     elif self._calibration_direction.get_value() == DOWN.get_value():
        #         self.absolute_position += run_distance

        # elif self._running_direction.get_value() == DOWN.get_value():
        #     if self._calibration_direction.get_value() == UP.get_value():
        #         self.absolute_position += run_distance

        #     elif self._calibration_direction.get_value() == DOWN.get_value():
        #         self.absolute_position -= run_distance

        if self._running_direction.get_value() is self._calibration_direction.get_value():
            self.absolute_position -= run_distance
        elif self._running_direction.get_value() is not self._calibration_direction.get_value():
            self.absolute_position += run_distance
        return
    
    def abort(self):
        '''
        Stop the running motor before it has completed a previously specified task.

        Returns
        -------
        run_interval : float
            The time interval the motor has been running for before being
            aborted, given in seconds.
        run_distance : float
            The distance travelled by the motor before being aborted,
            given in mm.
        '''
        if self.is_running:
            # Stop running timer
            self._running_timer.cancel()

            # Stop the current run
            run_interval, run_distance = self._stop()
        else:
            run_interval = None
            run_distance = None

        return run_interval, run_distance
    
    def calibrate(self, speed:float, direction:stepper.Direction = DOWN, is_linear:bool=True, calibration_timeout:bool = True):
        self.is_calibrated = False
        
        if not self.is_running:
            self.motor_start(speed, direction, is_linear)

            if direction.get_value() == UP.get_value():
                selected_endstop = self._endstop_up
            elif direction.get_value() == DOWN.get_value():
                selected_endstop = self._endstop_down
            
            timeout = None
            if calibration_timeout is True:
                max_distance = 130
                timeout = self._get_interval_from_distance(speed, max_distance, is_linear)
            
            has_reached_endstop = selected_endstop.wait_for_active(timeout)

            self.motor_stop()

            self.is_calibrated = has_reached_endstop

            self.is_calibrated = True

            if self.is_calibrated:
                self.absolute_position = 0
                self._calibration_direction = direction
        else:
            self.is_calibrated = False

        return self.is_calibrated
    
    def motor_start(self, speed:float, direction:stepper.Direction = DOWN, is_linear:bool=True):
        if not self.is_running:
            if is_linear:
                speed = self._get_rotational_speed(speed)

            self._motor.start(speed, direction)

            self.is_running = True
            self._running_direction = direction
            self._rotational_speed = speed
            
        return
    
    def motor_stop(self):
        run_interval, run_distance = self._stop()
        return run_interval, run_distance
    
    def run(self, speed:float, distance:float, direction:stepper.Direction, is_linear:bool=True):
        '''
        Run the motor for a specified task
        (speed, distance, and direction).
        The motor is automatically stopped once
        the task is completed.
        If the motor is already running, nothing happens.

        Parameters
        ----------
        speed : float
            The speed to run the motor at.
            It can be expressed in mm/s (linear)
            or RPS (rotational).
            Default is in mm/s (linear).
        distance : float
            The distance to travel to,
            given in mm.
        direction : Direction
            The direction to travel to.
        is_linear : bool, default=True
            If True it means that the speed is given
            in mm (linear), while if False it means that
            it is given in RPS (rotational).

        Returns
        -------
            interval : float
                The expected time interval to reach
                the specified destination at the
                desired speed, given in seconds.
            distance : float
                The distance to reach the specified
                destination, given in mm.
            started_at : float
                The time at which the motor is started.
        '''
        if not self.is_running:
            # Compute the run time interval
            interval = self._get_interval_from_distance(speed, distance, is_linear)
            
            # Init the timer
            self._running_timer = Timer(interval, self._stop)

            # Get the rotational speed, if necessary
            if is_linear:
                speed = self._get_rotational_speed(speed)
            
            # print(f'Run for {interval} s at {speed} rps')

            # Start the motor
            started_at = self._motor.start(speed, direction)

            # Start the timer
            self._running_timer.start()

            # Set running attributes
            self.is_running = True
            self._running_direction = direction
            self._rotational_speed = speed
        else:
            print('The motor is already running')
            interval = None
            distance = None
        
        return interval, distance, started_at

    def run_to(self):
        # run to a specified absolute point
        return
