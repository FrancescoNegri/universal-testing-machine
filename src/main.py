import stepper
import controller

motor = stepper.StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO)

control = controller.LinearController(motor, 1.5)
control.run(1, 3, controller.DOWN)

