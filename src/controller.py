import stepper
from threading import Timer

UP = stepper.CCW
DOWN = stepper.CW


class LinearController():
    def __init__(self, motor:stepper.StepperMotor, screw_pitch:float):
        self._motor = motor
        self._screw_pitch = screw_pitch

    def _get_time_from_distance(self, speed:float, distance:float, is_linear:bool=True):
        if is_linear:
            time = distance/speed
        else:
            #TODO
            time = distance/(speed * self._screw_pitch)

        return time

    def _get_rotational_speed(self, linear_speed:float):
        '''
        Convert a desired linear speed into the equivalent
        rotational speed.

        Parameters
        ----------
        linear_speed : float
            The desired linear speed expressed in mm/s.

        Return
        ------
        rotational_speed : float
            A rotational speed equivalent to the given linear speed
            expressed in RPS (revolutions-per-second).
        '''
        rotational_speed = linear_speed / self._screw_pitch
        return rotational_speed
    
    def run(self, speed:float, distance:float, direction:bool, is_linear:bool=True):        
        interval = self._get_time_from_distance(speed, distance, is_linear)
        run_timer = Timer(interval, self._motor.stop)

        if is_linear:
            speed = self._get_rotational_speed(speed)
        
        print('Run for {} s at {} rps'.format(interval, speed))
        self._motor.run(speed, direction)
        run_timer.start()
        
        return