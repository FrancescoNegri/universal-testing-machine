from statistics import mean
import sys
from threading import Timer

import stepper
import controller
import load_cell
import time
import numpy as np

import matplotlib.pyplot as plt

from gpiozero import Button

def start_section(name):
    print(f'\n\t\t{name}')
    print('--------------------------------------------------')
    return

def end_section():
    print('--------------------------------------------------')
    return

def delete_last_lines(n_lines:int=1):
    for _ in range(n_lines):
        #cursor up one line
        sys.stdout.write('\x1b[1A')

        #delete last line
        sys.stdout.write('\x1b[2K')

def calibrate(my_controller, my_load_cell):
    try:
        start_section('CALIBRATION')
        print('Calibrating the crossbar...')
        is_calibrated = my_controller.calibrate(speed=6, direction=controller.DOWN, is_linear=False)
        if is_calibrated:
            delete_last_lines(1)
            print('Calibrating the crossbar... Done')

        print('Adjusting crossbar position...')
        my_controller.run(speed=6, distance=25, direction=controller.UP, is_linear=False)
        while my_controller.is_running:
            pass
        delete_last_lines(1)
        print('Adjusting crossbar position... Done')

    except:
        motor.stop()

    print('Calibrating the load cell...\n')
    _, printed_lines = my_load_cell.calibrate(calibrating_mass=298.27)

    delete_last_lines(printed_lines + 2)
    print('Calibrating the load cell... Done')

    end_section()
    return

def execute_manual_mode(my_controller:controller.LinearController, my_load_cell:load_cell.LoadCell):
    start_section('MANUAL MODE')
    
    mode = 0

    button_mode = Button(11)

    def switch_mode():
        nonlocal mode
        mode = 1
        return

    button_mode.when_released = lambda: switch_mode()

    button_up = Button(17)
    button_down = Button(27)

    def direction_button_released():
        time.sleep(0.05)
        my_controller.motor_stop()

        return

    button_up.when_pressed = lambda: my_controller.motor_start(5, controller.UP)
    button_up.when_released = lambda: direction_button_released()

    button_down.when_pressed = lambda: my_controller.motor_start(5, controller.DOWN)
    button_down.when_released = lambda: direction_button_released()

    print('Now you are allowed to manually \nmove the crossbar up and down.')
    print('\nWaiting for manual mode to be stopped...')
    printed_lines = 1

    my_load_cell.start_reading()

    # my_timer = Timer(5, switch_mode)
    # my_timer.start()
    
    while mode == 0:
        batch_size = 20
        if my_load_cell.is_ready(batch_size):
            if printed_lines > 1:
                delete_last_lines(printed_lines - 1)
                printed_lines -= printed_lines - 1
            
            batch, _ = my_load_cell.get_measurement(batch_size)
            print(f'\nMeasured weight: {mean(batch)} g | Absolute position: {my_controller.absolute_position} mm')
            printed_lines += 2

    my_load_cell.stop_reading()
    
    delete_last_lines(printed_lines)
    print('Waiting for manual mode to be stopped... Done')
    end_section()

    return

def setup_test():
    start_section('TEST SETUP')

    printed_lines = 0

    print('Waiting for sample cross-section...\n')
    printed_lines += 2
    cross_section = input('Insert sample cross section in mm²: ')
    printed_lines += 1
    delete_last_lines(printed_lines)
    printed_lines -= printed_lines
    print('Waiting for sample cross-section... Done')

    print('Waiting for the displacement to reach...\n')
    printed_lines += 2
    displacement = input('Insert the desired displacement in mm: ')
    printed_lines += 1
    delete_last_lines(printed_lines)
    printed_lines -= printed_lines
    print('Waiting for the displacement to reach... Done')

    print('Waiting for the crossbar linear speed...\n')
    printed_lines += 2
    linear_speed = input('Insert the desired linear \nspeed for the crossbar in mm/s: ')
    printed_lines += 2
    delete_last_lines(printed_lines)
    printed_lines -= printed_lines
    print('Waiting for the crossbar linear speed... Done')    

    end_section()

    setup = {
        'CROSS SECTION': {
            'value': float(cross_section),
            'unit': 'mm²'
        },
        'DISPLACEMENT': {
            'value': float(displacement),
            'unit': 'mm'
        },
        'SPEED (mm/s)': {
            'value': float(linear_speed),
            'unit': 'mm/s'
        }
    }

    return setup

def check_test_setup(setup:dict):
    start_section('CHECK TEST PARAMETERS')

    for key in setup:
        value = setup[key]['value']
        unit = setup[key]['unit']
        print(f'{key} = {value} {unit}')

    input('\nPress ENTER to start...')
    delete_last_lines(1)
    print('Press ENTER to start... Done')

    end_section()

    return

if __name__ == '__main__':
    motor = stepper.StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO)
    control = controller.LinearController(motor, screw_pitch=1.5, pin_end_down=8, pin_end_up=25)
    lc = load_cell.LoadCell(dat_pin=5, clk_pin=6)

    calibrate(control, lc)
    execute_manual_mode(control, lc)
    setup = setup_test()
    check_test_setup(setup)
    

    # fig = plt.figure()
    # ax2=plt.axes()
    # line, = ax2.plot([], lw=3)
    # text = ax2.text(0.8,0.5, "")
    # ax2.set_xlim(0, 18+2)
    # ax2.set_ylim([0, 350])
    # fig.canvas.draw()   # note that the first draw comes before setting data

    # ax2background = fig.canvas.copy_from_bbox(ax2.bbox)

    # plt.show(block=False)

    # load = []
    # timing = []
    # line.set_data(timing,load)

    # lc.start_reading()

    # i = 0
    # while i < 100:
    #     if lc.is_ready():
    #         i += 1
    #         print('\n')
    #         print(i)
    #         batch, batch_index = lc.get_measurement()
    #         time_labels = np.arange(batch_index, batch_index+5, 1)*1/80
    #         load.extend(batch)
    #         timing.extend(time_labels)
            
    #         line.set_data(timing, load)
            
    #         print(batch)
    #         print(time_labels)

    #         # restore background
    #         fig.canvas.restore_region(ax2background)

    #         # redraw just the points
    #         ax2.draw_artist(line)
    #         ax2.draw_artist(text)

    #         # fill in the axes rectangle
    #         fig.canvas.blit(ax2.bbox)

    #         # in this post http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
    #         # it is mentionned that blit causes strong memory leakage.
    #         # however, I did not observe that.
    #         fig.canvas.flush_events()

    # n_readings = lc.stop_reading()
    # print(f'plotted data: {len(load)}')
    # print(f'sensor data: {n_readings}')


    # GPIO.cleanup()