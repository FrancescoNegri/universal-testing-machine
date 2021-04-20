import stepper
import controller
import load_cell
import time
import numpy as np

import RPi.GPIO as GPIO
import matplotlib.pyplot as plt

from gpiozero import Button

if __name__ == '__main__':
    motor = stepper.StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO)
    control = controller.LinearController(motor, screw_pitch=1.5, pin_end_down=8, pin_end_up=25)

    lc = load_cell.LoadCell(dat_pin=5, clk_pin=6)

    try:
        print('Calibrating the crossbar...')
        print(f'Done. Successful calibration: {control.calibrate(6, controller.DOWN, False)}')

        control.run(speed=6, distance=25, direction=controller.UP, is_linear=False)
        while control.is_running:
            pass

        print(f'Crossbar located at {control.absolute_position} mm.')
    except:
        motor.stop()

    print('Calibrating the load cell...')
    lc.calibrate(calibrating_mass=298.27)
    print('Done.')
    print('\nSwitching to manual mode to load the sample.')
    time.sleep(1)
    mode = 0

    button_up = Button(27)
    button_down = Button(17)
    button_up.hold_time =0.1
    button_down.hold_time =0.1

    button_up.when_held = lambda: control.motor_start(5, controller.UP)
    button_up.when_released = lambda: control.motor_stop()

    button_up.when_held = lambda: control.motor_start(5, controller.DOWN)
    button_up.when_released = lambda: control.motor_stop()

    while mode == 0:
        pass

    fig = plt.figure()
    ax2=plt.axes()
    line, = ax2.plot([], lw=3)
    text = ax2.text(0.8,0.5, "")
    ax2.set_xlim(0, 18+2)
    ax2.set_ylim([0, 350])
    fig.canvas.draw()   # note that the first draw comes before setting data

    ax2background = fig.canvas.copy_from_bbox(ax2.bbox)

    plt.show(block=False)

    load = []
    timing = []
    line.set_data(timing,load)

    lc.start_reading()

    i = 0
    while i < 100:
        if lc.is_ready():
            i += 1
            print('\n')
            print(i)
            batch, batch_index = lc.get_measurement()
            time_labels = np.arange(batch_index, batch_index+5, 1)*1/80
            load.extend(batch)
            timing.extend(time_labels)
            
            line.set_data(timing, load)
            
            print(batch)
            print(time_labels)

            # restore background
            fig.canvas.restore_region(ax2background)

            # redraw just the points
            ax2.draw_artist(line)
            ax2.draw_artist(text)

            # fill in the axes rectangle
            fig.canvas.blit(ax2.bbox)

            # in this post http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
            # it is mentionned that blit causes strong memory leakage.
            # however, I did not observe that.
            fig.canvas.flush_events()

    n_readings = lc.stop_reading()
    print(f'plotted data: {len(load)}')
    print(f'sensor data: {n_readings}')


    GPIO.cleanup()