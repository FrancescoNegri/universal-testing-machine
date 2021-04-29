from statistics import mean
import sys

import stepper
import controller
import load_cell
import numpy as np
import pandas as pd
import scipy.signal
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
        my_controller.run(speed=6, distance=55, direction=controller.UP, is_linear=False)
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

    button_mode = Button(7)

    def switch_mode():
        nonlocal mode
        mode = 1
        return

    button_mode.when_released = lambda: switch_mode()

    button_up = Button(17)
    button_down = Button(27)

    button_up.when_pressed = lambda: my_controller.motor_start(5, controller.UP)
    button_up.when_released = lambda: my_controller.motor_stop()

    button_down.when_pressed = lambda: my_controller.motor_start(5, controller.DOWN)
    button_down.when_released = lambda: my_controller.motor_stop()

    print('Now you are allowed to manually \nmove the crossbar up and down.')
    print('\nWaiting for manual mode to be stopped...')
    printed_lines = 1

    my_load_cell.start_reading()
    
    # my_timer = Timer(5, switch_mode)
    # my_timer.start()
    
    batch_index = 0
    batch_size = 20

    while mode == 0:
        if my_load_cell.is_batch_ready(batch_index, batch_size):
            if printed_lines > 1:
                delete_last_lines(printed_lines - 1)
                printed_lines -= printed_lines - 1
            
            batch, batch_index, _ = my_load_cell.get_batch(batch_index, batch_size)
            print(f'\nMeasured force: {round(mean(batch), 3)} N | Absolute position: {round(my_controller.absolute_position, 2)} mm')
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

def execute_test(my_controller:controller.LinearController, my_load_cell:load_cell.LoadCell, cross_section:float, distance:float, speed:float):
    # Plot initialization
    fig = plt.figure()
    ax = plt.axes()
    line, = ax.plot([], lw=3)
    text = ax.text(0.8, 0.5, '')

    clamps_initial_distance = 21.5
    initial_gauge_length = my_controller.absolute_position + clamps_initial_distance

    ax.set_xlim([0, round(((displacement / initial_gauge_length) * 1.1) * 100)]) # 10% margin
    ax.set_ylim([0, 30])
    fig.canvas.draw()   # note that the first draw comes before setting data

    ax_background = fig.canvas.copy_from_bbox(ax.bbox)

    plt.show(block=False)

    stress = []
    strain = []
    line.set_data(strain, stress)

    flag = 1
    
    _, _, t0 = my_controller.run(speed, distance, controller.UP, is_linear=True)
    
    batch_index = 0

    while my_controller.is_running:
        if flag == 1:
            my_load_cell.start_reading()
            flag=0
        if my_load_cell.is_batch_ready(batch_index):
            batch, batch_index, _ = my_load_cell.get_batch(batch_index)
            batch['t'] = batch['t'] - t0

            stresses = batch['F'] / cross_section                           # in N/mm2 = MPa
            strains = (batch['t'] * speed / initial_gauge_length) * 100     # in percentage 
            
            stress.extend(stresses)
            strain.extend(strains)

            line.set_data(strain, stress)

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
    data['stress_unfiltered'] = data['F'] / cross_section                   # in N/mm2 = MPa

    data['F'] = scipy.signal.medfilt(data['F'], 5)
    data['stress'] = data['F'] / cross_section                              # in N/mm2 = MPa

    data['strain'] = (data['t'] * speed / initial_gauge_length) * 100       # in percentage

    print(f'# plotted data: {len(stress)}')
    print('# collected data: {}'.format(len(data['stress'])))
    print(f'# initial gauge length: {initial_gauge_length}')
    
    # Save pandas DataFrame as an Excel file
    data.to_excel('test_data.xlsx', sheet_name='Sheet1', header=False, index=False)

    print('Press Enter to end the test')    

    return

if __name__ == '__main__':
    motor = stepper.StepperMotor(total_steps=200, dir_pin=20, step_pin=13, en_pin=23, mode_pins=(14, 15, 18), mode=stepper.ONE_THIRTYTWO)
    control = controller.LinearController(motor, screw_pitch=1.5, pin_end_down=8, pin_end_up=25)
    lc = load_cell.LoadCell(dat_pin=5, clk_pin=6)

    calibrate(control, lc)
    execute_manual_mode(control, lc)
    setup, cross_section, displacement, linear_speed = setup_test()
    check_test_setup(setup)
    execute_test(control, lc, cross_section, displacement, linear_speed)