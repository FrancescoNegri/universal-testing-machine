import os
import math
from statistics import mean
from InquirerPy import inquirer, validator
from rich import box
from rich.console import Console
from rich.table import Table
console = Console()
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
            validate=validator.NumberValidator(float_allowed=True)
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

def calibrate_controller(my_controller:controller.LinearController):
    with console.status('Calibrating the crossbar...'):
        is_calibrated = my_controller.calibrate(speed=0.75, direction=controller.DOWN, is_linear=False)
    
    if is_calibrated:
        console.print('[#e5c07b]>[/#e5c07b]', 'Calibrating the crossbar...', '[green]:heavy_check_mark:[/green]')
    else:
        console.print('[#e5c07b]>[/#e5c07b]', 'Calibrating the crossbar...', '[red]:cross_mark:[/red]')
    
    return

def adjust_crossbar_position(my_controller:controller.LinearController, adjustment_position:float):
    with console.status('Adjusting crossbar position...'):
        my_controller.run(speed=5, distance=adjustment_position, direction=controller.UP)
        while my_controller.is_running:
            pass
        
        if abs(my_controller.absolute_position - adjustment_position) > 0.01 * adjustment_position:
            console.print('[#e5c07b]>[/#e5c07b]', 'Adjusting crossbar position...', '[red]:cross_mark:[/red]')
        else:
            console.print('[#e5c07b]>[/#e5c07b]', 'Adjusting crossbar position...', '[green]:heavy_check_mark:[/green]')

    return

def start_manual_mode(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, speed:float, mode_button_pin:int, up_button_pin:int, down_button_pin:int):
    mode = 0
    def switch_mode():
        nonlocal mode
        mode = 1
        return

    mode_button = Button(pin=mode_button_pin, bounce_time=0.05)
    up_button = Button(pin=up_button_pin, bounce_time=0.05)
    down_button = Button(pin=down_button_pin, bounce_time=0.05)
    
    mode_button.when_released = lambda: switch_mode()
    up_button.when_pressed = lambda: my_controller.motor_start(speed, controller.UP)
    up_button.when_released = lambda: my_controller.motor_stop()
    down_button.when_pressed = lambda: my_controller.motor_start(speed, controller.DOWN)
    down_button.when_released = lambda: my_controller.motor_stop()

    batch_index = 0
    batch_size = 20
    my_loadcell.start_reading()

    force = '-'
    absolute_position = '-'

    console.print('[#e5c07b]>[/#e5c07b]', 'Now you are allowed to manually move the crossbar up and down.')
    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for manual mode to be stopped...')
    printed_lines = 1
    while mode == 0:
        if printed_lines > 1:
            utility.delete_last_lines(printed_lines - 1)
            printed_lines -= printed_lines - 1
        
        if my_loadcell.is_calibrated:
            if my_loadcell.is_batch_ready(batch_index, batch_size):                
                batch, batch_index, _ = my_loadcell.get_batch(batch_index, batch_size)
                force = round(mean(batch['F']), 5)

        if my_controller.is_calibrated:
            try:
                absolute_position = round(my_controller.absolute_position, 2)
            except:
                absolute_position = '-'
        
        table = Table(box=box.ROUNDED)
        table.add_column('Force', justify='center', min_width=12)
        table.add_column('Absolute position', justify='center', min_width=20)
        table.add_row(f'{force} N', f'{absolute_position} mm')
        console.print(table)
        printed_lines += 5

        if down_button.is_active and my_controller._down_endstop.is_active:
            my_controller.motor_stop()
        if up_button.is_active and my_controller._up_endstop.is_active:
            my_controller.motor_stop()

    my_loadcell.stop_reading()
    
    mode_button.when_released = None
    up_button.when_pressed = None
    up_button.when_released = None
    down_button.when_pressed = None
    down_button.when_released = None
    
    utility.delete_last_lines(printed_lines)
    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for manual mode to be stopped...', '[green]:heavy_check_mark:[/green]')
    
    return

def read_test_parameters(is_cyclic:bool):
    is_confirmed = False

    while not is_confirmed:
        cross_section = inquirer.text(
            message='Insert the sample cross section [mm²]:',
            validate=validator.NumberValidator(float_allowed=True)
        ).execute()

        displacement = inquirer.text(
            message='Insert the desired displacement [mm]:',
            validate=validator.NumberValidator(float_allowed=True)
        ).execute()

        linear_speed = inquirer.text(
            message='Insert the desired linear speed [mm/s]:',
            validate=validator.NumberValidator(float_allowed=True)
        ).execute()

        is_confirmed = inquirer.confirm(
            message='Confirm?'
        ).execute()

    test_parameters = {
        'cross_section': {
            'value': float(cross_section),
            'unit': 'mm²'
        },
        'displacement': {
            'value': float(displacement),
            'unit': 'mm'
        },
        'linear_speed': {
            'value': float(linear_speed),
            'unit': 'mm/s'
        }
    }

    return test_parameters