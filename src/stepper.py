import os
import time
import pigpio

class Direction():
    def __init__(self, value:bool):
        '''
        Class for motor direction.

        Parameters
        ----------
        value: bool
        '''
        self._value = value
    def get_value(self):
        '''
        Return the direction.
        '''
        return self._value

CCW = Direction(1)
CW = Direction(0)

class Mode():
    def __init__(self, microstep_size:float, M0:bool, M1:bool, M2:bool):
        '''
        Class for motor running mode.

        Parameters
        ----------
        microstep_size : float
            Microstep size for the specified mode with respect to a full step.
        M0 : bool
            Value for the M0 pin.
        M1 : bool
            Value for the M1 pin.
        M2 : bool
            Value for the M2 pin.
        '''
        self._M0 = M0
        self._M1 = M1
        self._M2 = M2
        self._microstep_size = microstep_size

    def get_values(self):
        '''
        Return a tuple representing the values for each
        mode pin.
        '''
        return (self._M0, self._M1, self._M2)

    def get_microstep_size(self):
        '''
        Return the microstep size for this mode.
        '''
        return self._microstep_size
    
FULL = Mode(1, 0, 0, 0)
HALF = Mode(1/2, 1, 0, 0)
ONE_FOUR = Mode(1/4, 0, 1, 0)
ONE_EIGHT = Mode(1/8, 1, 1, 0)
ONE_SIXTEEN = Mode(1/16, 0, 0, 1)
ONE_THIRTYTWO = Mode(1/32, 1, 0, 1)

class StepperMotor():

    def __init__(self, total_steps:int, dir_pin:int, step_pin:int, en_pin:int, mode_pins:tuple, mode:Mode=FULL):
        '''
        Class for stepper motors.

        This class specifies an interface to control stepper motors
        through PWM technique.

        Parameters
        ----------
        total_steps : int
            The total number of steps to complete one revolution for the employed stepper motor.
        dir_pin : int
            The direction (DIR) pin.
        step_pin : int
            The step (STEP) pin.
        en_pin : int
            The enable (EN) pin.
        mode_pins : tuple
            The three pins (M0, M1, M2) determining the motor mode.
        mode : Mode, default=FULL
            The motor mode to use.
        '''
        self._total_steps = total_steps
        self._dir_pin = dir_pin
        self._step_pin = step_pin
        self._en_pin = en_pin
        self._mode_pins = mode_pins
        self._mode = mode
        self._start_at = None

        try:
            os.system("sudo pigpiod")
        finally:
            time.sleep(1)
        
        # Connect to pigpio daemon
        self._pi = pigpio.pi()

        # Set up pins as an output
        self._pi.set_mode(self._dir_pin, pigpio.OUTPUT)
        self._pi.set_mode(self._step_pin, pigpio.OUTPUT)
        self._pi.set_mode(self._en_pin, pigpio.OUTPUT)

        # Disable the stepper motor (active-low logic)
        self._pi.write(self._en_pin, 1)

        # Set the given mode
        self.set_mode(mode)
        
    def _get_RPS_from_RPM(self, RPM:float):
        ''' 
        Return the RPS (revolutions-per-second)
        given the RPM (revolutions-per-minute).

        Parameters
        ----------
        RPM : float
            The amount of RPM to convert.

        Returns
        -------
        RPS : float
            The amount of RPS computed.
        '''
        RPS = RPM / 60
        return RPS

    def _get_RPM_from_RPS(self, RPS:float):
        ''' 
        Return the RPM (revolutions-per-minute)
        given the RPS (revolutions-per-seconds).

        Parameters
        ----------
        RPS : float
            The amount of RPS to convert.

        Returns
        -------
        RPM : float
            The amount of RPM computed.
        '''
        RPM = RPS * 60
        return RPM

    def _get_PWMfreq_from_RPM(self, RPM:float):
        ''' 
        Return the PWM frequency needed to
        rotate at the given RPM (revolutions-per-minute).
        The PWM frequency is then rounded to an integer.

        Parameters
        ----------
        RPM : float
            The amount of RPM to rotate at.

        Returns
        -------
        PWMfreq : int
            The PWM frequency computed.
        '''

        RPS = self._get_RPS_from_RPM(RPM)
        PWMfreq = self._get_PWMfreq_from_RPS(RPS)
        return PWMfreq

    def _get_PWMfreq_from_RPS(self, RPS:float):
        ''' 
        Return the PWM frequency needed to
        rotate at the given RPS (revolutions-per-second).
        The PWM frequency is then rounded to an integer.

        Parameters
        ----------
        RPS : float
            The amount of RPS to rotate at.

        Returns
        -------
        PWMfreq : int
            The PWM frequency computed.
        '''

        PWMfreq_revolution = self._total_steps / self._mode.get_microstep_size()

        # 1 rps : PWMfreq_revolution = RPS : PWMfreq
        PWMfreq = RPS * PWMfreq_revolution
        PWMfreq = round(PWMfreq)
        return PWMfreq

    def set_mode(self, mode:Mode):
        '''
        Set the employed motor mode.

        Parameters
        ----------
        mode : Mode
            The motor mode to use.
        '''
        self._mode = mode

        for pin in self._mode_pins:
            idx = self._mode_pins.index(pin)
            self._pi.write(pin, self._mode.get_values()[idx])
            # print('Pin {} = {}'.format(pin, self._mode.get_values()[idx]))

        return

    def start(self, speed:float, direction:Direction, is_RPM:bool = False):
        '''
        Start the stepper motor at the specified speed and in the given direction.

        Parameters
        ----------
        speed : float
            The speed to run the motor at, expressed in RPM or RPS. Default is RPS.
        direction : Direction
            The direction given to the stepper motor.
        is_RPM : bool, default=False
            If True it means that the speed is expressed in RPM (revolutions-per-minute),
            while if False it means that the speed is expressed in RPS (revolutions-per-second).
        '''
        # Enable the stepper motor (active-low logic)
        self._pi.write(self._en_pin, 0)
        time.sleep(0.05)
        
        # Set the stepper motor direction
        self._pi.write(self._dir_pin, direction.get_value())  # Set direction. 0 DOWN, 1 UP
        time.sleep(0.05)

        # Set duty cycle and frequency
        if is_RPM:
            PWMfreq = self._get_PWMfreq_from_RPM(speed)
        else:
            PWMfreq = self._get_PWMfreq_from_RPS(speed)

        self._pi.hardware_PWM(self._step_pin, PWMfreq, 500000) # 2000Hz 50% dutycycle
        
        # Set start time
        self._start_at = time.time()

        return

    def stop(self):
        '''
        Stop the stepper motor. 
        
        Return
        ------
        running_time : float | None
            The amount of time the motor has been running in seconds.
            If the motor is not running, None is returned.
        '''
        # Turn off the PWM
        self._pi.hardware_PWM(self._step_pin, 0, 0)
        
        # Get running time
        running_time = self.get_running_time()
        self._start_at = None
        
        # Disable the stepper motor (active-low logic)
        self._pi.write(self._en_pin, 1)
        time.sleep(0.05)

        return running_time

    def get_running_time(self):
        '''
        Get the amount of time the motor has been running.

        Return
        ------
        running_time : float | None
            The amount of time the motor has been running in seconds.
            If the motor is not running, None is returned.
        '''
        if self._start_at is not None:
            running_time = time.time() - self._start_at
        else:
            running_time = None
        return running_time