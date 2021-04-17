import stepper
import controller
import time

if __name__ == '__main__':
    motor = stepper.StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO)

    control = controller.LinearController(motor, screw_pitch=1.5)
    interval = control.run(speed=2, distance=10, direction=controller.DOWN)

    time.sleep(3.2)

    running_time = control.abort()
    if running_time is None: running_time = interval
    
    print(f'\nMotor is running: {control.is_running}. \nIt ran for {running_time} s')