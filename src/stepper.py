import os
import pigpio
from time import sleep

from utils import get_PWMfreq_from_RPM, get_PWMfreq_from_RPS

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

UP = Direction(1)
DOWN = Direction(0)
CCW = Direction(1)
CW = Direction(0)

class Mode():
    def __init__(self, M0:bool, M1:bool, M2:bool):
        '''
        Class for motor running mode.

        Parameters
        ----------
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
    def get_values(self):
        '''
        Return a tuple representing the values for each
        mode pin.
        '''
        return (self._M0, self._M1, self._M2)
    
FULL = Mode(0, 0, 0)
HALF = Mode(1, 0, 0)
ONE_FOUR = Mode(0, 1, 0)
ONE_EIGHT = Mode(1, 1, 0)
ONE_SIXTEEN = Mode(0, 0, 1)
ONE_THIRTYTWO = Mode(1, 0, 1)

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

        try:
            os.system("sudo pigpiod")
        finally:
            sleep(1)
        
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
        
    def set_mode(self, mode:Mode):
        '''
        Set the employed motor mode.

        Parameters
        ----------
        mode : Mode
            The motor mode to use.
        '''
        self._mode = mode.get_values()

        for pin in self._mode_pins:
            idx = self._mode_pins.index(pin)
            self._pi.write(pin, self._mode[idx])
            # print('Pin {} = {}'.format(pin, self._mode[idx]))

        return

    def run(self, speed:float, direction:Direction, is_RPM:bool = True):
        '''
        Run the stepper motor at the specified speed and in the given direction.

        Parameters
        ----------
        speed : float
            The speed to run the motor at, expressed in RPM or RPS.
        direction : Direction
            The direction given to the stepper motor.
        is_RPM : bool, default=True
            If True it means that the speed is expressed in RPM (revolutions-per-minute),
            while if False it means that the speed is expressed in RPS (revolutions-per-second).
        '''
        # Enable the stepper motor (active-low logic)
        self._pi.write(self._en_pin, 0)
        sleep(0.05)
        
        # Set the stepper motor direction
        self._pi.write(self._dir_pin, direction.get_value())  # Set direction. 0 DOWN, 1 UP
        sleep(0.05)

        # Set duty cycle and frequency
        if is_RPM:
            PWMfreq = get_PWMfreq_from_RPM(speed)
        else:
            PWMfreq = get_PWMfreq_from_RPS(speed)

        self._pi.hardware_PWM(self._step_pin, PWMfreq, 500000) # 2000Hz 50% dutycycle
        return

    def stop(self):
        '''
        Stop the stepper motor.
        '''
        # Turn off the PWM
        self._pi.hardware_PWM(self._step_pin, 0, 0)
        
        # Disable the stepper motor (active-low logic)
        self._pi.write(self._en_pin, 1)
        return