from statistics import mean

import stepper
import controller
import load_cell
import numpy as np
import pandas as pd
import scipy.signal
import matplotlib.pyplot as plt
import utility

from gpiozero import Button

def calibrate(my_controller, my_load_cell, calibration_dir):
    utility.start_section('CALIBRATION')

    try:
        print('Calibrating the crossbar...')
        is_calibrated = my_controller.calibrate(speed=0.75, direction=controller.DOWN, is_linear=False)
        utility.delete_last_lines(1)
        if is_calibrated:
            print('Calibrating the crossbar... Done')
        else:
            print('Calibrating the crossbar... FAILED')

        print('Adjusting crossbar position...')
        my_controller.run(speed=5, distance=50, direction=controller.UP)
        while my_controller.is_running:
            pass
        utility.delete_last_lines(1)
        print('Adjusting crossbar position... Done')

        print('Calibrating the load cell...\n')
        is_calibrated = my_load_cell.calibrate(calibration_dir=calibration_dir, calibrating_mass=298.27)
        utility.delete_last_lines(2)
        if is_calibrated:
            print('Calibrating the load cell... Done')
        else:
            print('Calibrating the load cell... FAILED')

    except:
        motor.stop()

    utility.end_section()
    return

def execute_manual_mode(my_controller:controller.LinearController, my_load_cell:load_cell.LoadCell):
    utility.start_section('MANUAL MODE')
    
    mode = 0

    button_mode = Button(22)

    def switch_mode():
        nonlocal mode
        mode = 1
        return

    button_mode.when_released = lambda: switch_mode()

    button_up = Button(17)
    button_down = Button(27)
    button_speed_linear = 3

    button_up.when_pressed = lambda: my_controller.motor_start(button_speed_linear, controller.UP)
    button_up.when_released = lambda: my_controller.motor_stop()

    button_down.when_pressed = lambda: my_controller.motor_start(button_speed_linear, controller.DOWN)
    button_down.when_released = lambda: my_controller.motor_stop()

    print('Now you are allowed to manually \nmove the crossbar up and down.')
    print('\nWaiting for manual mode to be stopped...')
    printed_lines = 1

    my_load_cell.start_reading()
    
    # from threading import Timer
    # my_timer = Timer(5, switch_mode)
    # my_timer.start()
    
    batch_index = 0
    batch_size = 20

    while mode == 0:
        if my_load_cell.is_batch_ready(batch_index, batch_size):
            if printed_lines > 1:
                utility.delete_last_lines(printed_lines - 1)
                printed_lines -= printed_lines - 1
            
            batch, batch_index, _ = my_load_cell.get_batch(batch_index, batch_size)

            force = round(mean(batch['F']), 3)
            try:
                absolute_position = round(my_controller.absolute_position, 2)
            except:
                absolute_position = 0
            print(f'\nMeasured force: {force} N | Absolute position: {absolute_position} mm')
            printed_lines += 2

        if button_down.is_active and my_controller._endstop_down.is_active:
            my_controller.motor_stop()
        if button_up.is_active and my_controller._endstop_up.is_active:
            my_controller.motor_stop()

    my_load_cell.stop_reading()
    
    utility.delete_last_lines(printed_lines)
    print('Waiting for manual mode to be stopped... Done')
    utility.end_section()

    return

def setup_test():
    utility.start_section('TEST SETUP')

    printed_lines = 0

    print('Waiting for sample cross-section...\n')
    printed_lines += 2
    cross_section = input('Insert sample cross section in mm²: ')
    printed_lines += 1
    utility.delete_last_lines(printed_lines)
    printed_lines -= printed_lines
    print('Waiting for sample cross-section... Done')

    print('Waiting for the displacement to reach...\n')
    printed_lines += 2
    displacement = input('Insert the desired displacement in mm: ')
    printed_lines += 1
    utility.delete_last_lines(printed_lines)
    printed_lines -= printed_lines
    print('Waiting for the displacement to reach... Done')

    print('Waiting for the crossbar linear speed...\n')
    printed_lines += 2
    linear_speed = input('Insert the desired linear \nspeed for the crossbar in mm/s: ')
    printed_lines += 2
    utility.delete_last_lines(printed_lines)
    printed_lines -= printed_lines
    print('Waiting for the crossbar linear speed... Done')    

    utility.end_section()

    cross_section = float(cross_section)
    displacement = float(displacement)
    linear_speed = float(linear_speed)

    setup = {
        'CROSS SECTION': {
            'value': cross_section,
            'unit': 'mm²'
        },
        'DISPLACEMENT': {
            'value': displacement,
            'unit': 'mm'
        },
        'SPEED': {
            'value': linear_speed,
            'unit': 'mm/s'
        }
    }

    return setup, cross_section, displacement, linear_speed

def check_test_setup(setup:dict):
    utility.start_section('CHECK TEST PARAMETERS')

    for key in setup:
        value = setup[key]['value']
        unit = setup[key]['unit']
        print(f'{key} = {value} {unit}')

    input('\nPress ENTER to start...')
    utility.delete_last_lines(1)
    print('Press ENTER to start... Done')

    utility.end_section()

    return

def execute_test(my_controller:controller.LinearController, my_load_cell:load_cell.LoadCell, cross_section:float, distance:float, speed:float):
    utility.start_section('TEST RESULTS')
    
    # Plot initialization
    fig = plt.figure()
    ax = plt.axes()
    line, = ax.plot([], lw=3)
    text = ax.text(0.8, 0.5, '')

    clamps_initial_distance = 21.5
    initial_gauge_length = my_controller.absolute_position + clamps_initial_distance

    ax.set_xlim([0, round(((displacement / initial_gauge_length) * 1.1) * 100)]) # 10% margin
    ax.set_ylim([0, 10])
    fig.canvas.draw()   # note that the first draw comes before setting data

    ax_background = fig.canvas.copy_from_bbox(ax.bbox)

    plt.show(block=False)

    force = []
    strain = []
    line.set_data(strain, force)

    _, _, t0 = my_controller.run(speed, distance, controller.UP, is_linear=True)
    my_load_cell.start_reading()

    batch_index = 0

    while my_controller.is_running:
        if my_load_cell.is_batch_ready(batch_index):
            batch, batch_index, _ = my_load_cell.get_batch(batch_index)
            batch['t'] = batch['t'] - t0

            # stresses = batch['F'] / cross_section                           # in N/mm2 = MPa
            strains = (batch['t'] * speed / initial_gauge_length) * 100     # in percentage 
            
            force.extend(batch['F'])
            strain.extend(strains)

            line.set_data(strain, force)

            # restore background
            fig.canvas.restore_region(ax_background)

            # redraw just the points
            ax.draw_artist(line)
            ax.draw_artist(text)

            # fill in the axes rectangle
            fig.canvas.blit(ax.bbox)

            # in this post http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
            # it is mentionned that blit causes strong memory leakage.
            # however, I did not observe that.
            fig.canvas.flush_events()

    data, _ = my_load_cell.stop_reading()

    data['t'] = data['t'] - t0

    data['F_unfiltered'] = data['F']
    data['F'] = scipy.signal.medfilt(data['F'], 5)

    data['stress'] = data['F'] / cross_section                              # in N/mm2 = MPa
    data['stress_unfiltered'] = data['F_unfiltered'] / cross_section        # in N/mm2 = MPa

    data['strain'] = (data['t'] * speed / initial_gauge_length) * 100       # in percentage

    # TODO: add other data to the output file -> initial_gauge_length, test parameters, etc...

    print(f'# plotted data: {len(force)}')
    print('# collected data: {}'.format(len(data['F'])))
    print(f'# initial gauge length: {initial_gauge_length}')
    
    # TODO: save the output file in an output folder with a unique (timestamp ?) filename

    # Save pandas DataFrame as a CSV file
    data.to_csv('test_data.csv', index=False)

    input('\nPress ENTER to end the test...')
    utility.delete_last_lines(1) 
    print('Press ENTER to end the test... Done') 

    utility.end_section()  

    return

if __name__ == '__main__':
    motor = stepper.StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO, gear_ratio=5.18)
    control = controller.LinearController(motor, screw_pitch=5, pin_end_down=8, pin_end_up=25)
    lc = load_cell.LoadCell(dat_pin=5, clk_pin=6)

    output_dir, calibration_dir = utility.init_dirs()
    calibrate(control, lc, calibration_dir)
    execute_manual_mode(control, lc)
    setup, cross_section, displacement, linear_speed = setup_test()
    check_test_setup(setup)
    execute_test(control, lc, cross_section, displacement, linear_speed)