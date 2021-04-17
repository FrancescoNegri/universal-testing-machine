import stepper
import controller
import time

if __name__ == '__main__':
    motor = stepper.StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO)

    control = controller.LinearController(motor, screw_pitch=1.5)
    full_time, full_distance = control.run(speed=2, distance=10, direction=controller.DOWN)

    time.sleep(2.2)

    run_time, run_distance = control.abort()
    if run_time is None: run_time = full_time
    if run_distance is None: run_distance = full_distance
    
    print(f'\nMotor is running: {control.is_running}. \nIt ran for {run_time} s and for {run_distance} mm')