import stepper
import controller
import time

if __name__ == '__main__':
    motor = stepper.StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO)

    control = controller.LinearController(motor, screw_pitch=1.5, pin_end_down=27, pin_end_up=17)

    try:
        control.run(speed=5, distance=20, direction=controller.UP, is_linear=False)
    except:
        motor.stop()

    
    # full_interval, full_distance = control.run(speed=1, distance=10, direction=controller.DOWN)

    # time.sleep(2.2)

    # run_interval, run_distance = control.abort()
    # if run_interval is None and run_distance is None: 
    #     run_interval = full_interval
    #     run_distance = full_distance
    # else:
    #     print('Aborted.')
    
    # print(f'\nMotor ran for {run_interval} s and for {run_distance} mm')