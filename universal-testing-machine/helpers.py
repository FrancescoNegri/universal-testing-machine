import os
from statistics import mean
from InquirerPy import inquirer, validator
from datetime import datetime
import utility
import controller
import loadcell
import json
from gpiozero import Button

def create_calibration_dir():
    dir = os.path.dirname(__file__)
    path = '../.calibration'
    calibration_dir = os.path.join(dir, path)
    os.makedirs(calibration_dir, exist_ok=True)

    return calibration_dir

def create_output_dir():
    dir = os.path.dirname(__file__)
    path = '../output'
    output_dir = os.path.join(dir, path)
    os.makedirs(output_dir, exist_ok=True)

    date = datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
    output_dir = os.path.join(dir, path, date)
    os.makedirs(output_dir)

    return output_dir

def check_existing_calibration(calibration_dir:str, my_loadcell:loadcell.LoadCell):
    try:
        with open(calibration_dir + r'/' + my_loadcell._calibration_filename) as f:
            use_existing_calibration = inquirer.confirm(
                message='An existing calibration for the load cell has been found. Do you want to use it?',
                default=True
            ).execute()

            if use_existing_calibration:
                calibration = json.load(f)
                my_loadcell._slope = calibration['slope']
                my_loadcell._y_intercept = calibration['y_intercept']
                my_loadcell.is_calibrated = True
            else:
                my_loadcell.is_calibrated = False
    except:
        my_loadcell.is_calibrated = False

    return

def calibrate_loadcell(my_loadcell:loadcell.LoadCell, calibration_dir:str):
    calibrating_mass = inquirer.select(
        message='Select the calibrating mass value [g]:',
        choices=[
            {'name': '63.352 g (1 N load cell)', 'value': 63.352},
            {'name': '361.606 g (10 N load cell)', 'value': 361.606},
            {'name': 'Custom', 'value': None}
        ],
        default=361.606
    ).execute()

    if calibrating_mass is None:
        calibrating_mass = inquirer.text(
            message='Insert the desired calibrating mass [g]:',
            validate=validator.NumberValidator()
        ).execute()

    calibrating_mass = float(calibrating_mass)

    ready_zero = False
    while ready_zero is False:
        ready_zero = inquirer.confirm(
            message='Zero-mass point calibration. Ready?'
        ).execute()
    zero_raw = my_loadcell._get_raw_data_mean(n_readings=100, fake=True) #HACK#

    ready_mass = False
    while ready_mass is False:
        ready_mass = inquirer.confirm(
            message='Known-mass point calibration. Add the known mass. Ready?'
        ).execute()
    mass_raw = my_loadcell._get_raw_data_mean(n_readings=100, fake=True) #HACK#

    my_loadcell.calibrate(zero_raw, mass_raw, calibrating_mass, calibration_dir)

    return

def calibrate_controller(my_controller:controller.LinearController, adjustment_position:float):
    print('Calibrating the crossbar...')
    is_calibrated = my_controller.calibrate(speed=0.75, direction=controller.DOWN, is_linear=False)
    utility.delete_last_lines(1)
    if is_calibrated:
        print('Calibrating the crossbar... Done')
    else:
        print('Calibrating the crossbar... FAILED')

    print('Adjusting crossbar position...')
    my_controller.run(speed=5, distance=adjustment_position, direction=controller.UP)
    while my_controller.is_running:
        pass
    utility.delete_last_lines(1)
    print('Adjusting crossbar position... Done')

    return

def start_manual_mode(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, speed:float, mode_button_pin:int, up_button_pin:int, down_button_pin:int):
    mode = 0

    mode_button = Button(mode_button_pin)
    up_button = Button(up_button_pin)
    down_button = Button(down_button_pin)

    def switch_mode():
        nonlocal mode
        mode = 1
        return
    
    mode_button.when_released = switch_mode

    up_button.when_pressed = lambda: my_controller.motor_start(speed, controller.UP)
    up_button.when_released = lambda: my_controller.motor_stop()

    down_button.when_pressed = lambda: my_controller.motor_start(speed, controller.DOWN)
    down_button.when_released = lambda: my_controller.motor_stop()

    print('Now you are allowed to manually \nmove the crossbar up and down.')
    print('\nWaiting for manual mode to be stopped...')
    printed_lines = 4

    batch_index = 0
    batch_size = 20
    my_loadcell.start_reading()

    while mode == 0:
        if my_loadcell.is_calibrated:
            if my_loadcell.is_batch_ready(batch_index, batch_size):
                if printed_lines > 4:
                    utility.delete_last_lines(printed_lines - 4)
                    printed_lines -= printed_lines - 4
                
                batch, batch_index, _ = my_loadcell.get_batch(batch_index, batch_size)

                force = round(mean(batch['F']), 5)

                if my_controller.is_calibrated:
                    try:
                        absolute_position = round(my_controller.absolute_position, 2)
                    except:
                        absolute_position = 0
                    print(f'\nMeasured force: {force} N | Absolute position: {absolute_position} mm')
                    printed_lines += 2
                else:
                    print(f'\nMeasured force: {force} N')
                    printed_lines += 2

        if down_button.is_active and my_controller._endstop_down.is_active:
            my_controller.motor_stop()
        if up_button.is_active and my_controller._endstop_up.is_active:
            my_controller.motor_stop()

    my_loadcell.stop_reading()
    
    utility.delete_last_lines(printed_lines)
    print('Waiting for manual mode to be stopped... Done')
    
    return
