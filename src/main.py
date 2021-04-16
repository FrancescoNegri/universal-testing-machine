import stepper
from threading import Timer
from stepper import StepperMotor

motor = StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO)

myTimer = Timer(5, motor.stop)

motor.run(1, stepper.UP, False)
myTimer.start()