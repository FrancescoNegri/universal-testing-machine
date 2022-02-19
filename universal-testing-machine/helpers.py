import os
from statistics import mean
from InquirerPy import inquirer, validator
from rich import box
from rich.console import Console
from rich.table import Table
from rich.live import Live
console = Console()
from utility import utility
from controller import controller
from loadcell import loadcell
import json
import scipy.signal
from gpiozero import Button
from src import constants

def create_calibration_dir():
    dir = os.path.dirname(__package__)
    path = './.calibration'
    calibration_dir = os.path.join(dir, path)
    os.makedirs(calibration_dir, exist_ok=True)

    return calibration_dir

def create_output_dir(test_parameters:dict):
    dir = os.path.dirname(__package__)
    path = './output'
    output_dir = os.path.join(dir, path)
    os.makedirs(output_dir, exist_ok=True)

    test_id = test_parameters['test_id']
    output_dir = os.path.join(dir, path, test_id)
    copy_idx = ''
    idx = 0
    while os.path.isdir(output_dir + copy_idx):
        idx = idx + 1
        copy_idx = '(' + str(idx) + ')'
    output_dir = output_dir + copy_idx
    os.makedirs(output_dir)

    return output_dir

# TODO: refactor calibration as test_parameters
def check_existing_calibration(calibration_dir:str, my_loadcell:loadcell.LoadCell):
    try:
        with open(os.path.join(calibration_dir, my_loadcell._calibration_filename)) as f:
            calibration = json.load(f)
            use_existing_calibration = inquirer.confirm(
                message='An existing calibration for the {} {} load cell has been found. Do you want to use it?'.format(calibration['loadcell_limit']['value'], calibration['loadcell_limit']['unit']),
                default=True
            ).execute()

            if use_existing_calibration:
                my_loadcell.set_calibration(calibration)
            else:
                my_loadcell.is_calibrated = False
    except:
        my_loadcell.is_calibrated = False

    return

def calibrate_loadcell(my_loadcell:loadcell.LoadCell, calibration_dir:str):
    loadcell_type = inquirer.select(
        message='Selected the desired loadcell:',
        choices=[
            {'name': '1 N', 'value': 1},
            {'name': '10 N', 'value': 10}
        ],
        default=10,
    ).execute()

    loadcell_type = int(loadcell_type)

    calibrating_mass = inquirer.select(
        message='Select the calibrating mass value [g]:',
        choices=[
            {'name': f'{str(constants.CALIBRATING_MASS_1_N)} g (1 N load cell)', 'value': constants.CALIBRATING_MASS_1_N},
            {'name': f'{str(constants.CALIBRATING_MASS_10_N)} g (10 N load cell)', 'value': constants.CALIBRATING_MASS_10_N},
            {'name': 'Custom', 'value': None}
        ],
        default= constants.CALIBRATING_MASS_10_N if loadcell_type == 10 else constants.CALIBRATING_MASS_1_N
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
    zero_raw = my_loadcell._get_raw_data_mean(n_readings=100, fake=False) #HACK#

    ready_mass = False
    while ready_mass is False:
        ready_mass = inquirer.confirm(
            message='Known-mass point calibration. Add the known mass. Ready?'
        ).execute()
    mass_raw = my_loadcell._get_raw_data_mean(n_readings=100, fake=False) #HACK#

    my_loadcell.calibrate(loadcell_type, zero_raw, mass_raw, calibrating_mass, calibration_dir)

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
        
        if abs(my_controller.get_absolute_position() - adjustment_position) > 0.01 * adjustment_position:
            console.print('[#e5c07b]>[/#e5c07b]', 'Adjusting crossbar position...', '[red]:cross_mark:[/red]')
        else:
            console.print('[#e5c07b]>[/#e5c07b]', 'Adjusting crossbar position...', '[green]:heavy_check_mark:[/green]')

    return

def generate_data_table(force:float, absolute_position:float, loadcell_limit:float, force_offset:float, test_parameters:dict = None):
    if force is None:
        force = '-'
        loadcell_usage = '-'
        loadcell_usage_style = None
    elif loadcell_limit is None:
        force = round(force, 5)
        loadcell_usage = '-'
        loadcell_usage_style = None
    else:
        force = round(force, 5)
        if force_offset is None:
            force_offset = 0
        loadcell_usage = abs(round(((force + force_offset) / loadcell_limit) * 100, 2))
        loadcell_usage_style = 'red' if loadcell_usage > 85 else None

    if absolute_position is None:
        absolute_position = '-'
        test_progress = '-'
    else:
        absolute_position = round(absolute_position, 2)

        if test_parameters is None:
            test_progress = None
        elif test_parameters['test_type'] == 'monotonic':
            initial_absolute_position = test_parameters['initial_gauge_length']['value'] - test_parameters['clamps_distance']['value']
            test_progress = ((absolute_position - initial_absolute_position) / test_parameters['displacement']['value']) * 100
            test_progress = round(test_progress, 1)
        elif test_parameters['test_type'] == 'cyclic':
            pass

    table = Table(box=box.ROUNDED)
    table.add_column('Force', justify='center', min_width=12)
    table.add_column('Absolute position', justify='center', min_width=20)
    table.add_column('Load Cell usage', justify='center', min_width=12, style=loadcell_usage_style)

    if test_parameters is None:
        table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %')
    elif test_parameters['test_type'] == 'monotonic':
        table.add_column('Test progress', justify='center', min_width=12)        
        table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %', f'{test_progress} %')
    elif test_parameters['test_type'] == 'cyclic':
        table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %')

    return table

def start_manual_mode(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, speed:float, mode_button_pin:int, up_button_pin:int, down_button_pin:int):
    mode = 0
    def _switch_mode():
        nonlocal mode
        mode = 1
        return

    mode_button = Button(pin=mode_button_pin)
    up_button = Button(pin=up_button_pin)
    down_button = Button(pin=down_button_pin)
    
    mode_button.when_released = lambda: _switch_mode()
    up_button.when_pressed = lambda: my_controller.motor_start(speed, controller.UP)
    up_button.when_released = lambda: my_controller.motor_stop()
    down_button.when_pressed = lambda: my_controller.motor_start(speed, controller.DOWN)
    down_button.when_released = lambda: my_controller.motor_stop()

    if my_loadcell.is_calibrated:
        my_loadcell.start_reading()

    console.print('[#e5c07b]>[/#e5c07b]', 'Now you are allowed to manually move the crossbar up and down.')
    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for manual mode to be stopped...')
    printed_lines = 1
    
    force = None
    absolute_position = None
    loadcell_limit = my_loadcell.get_calibration()['loadcell_limit']['value'] if my_loadcell.is_calibrated else None
    force_offset = my_loadcell.get_offset(is_force=True) if my_loadcell.is_calibrated else None
    batch_index = 0
    batch_size = 25

    live_table = Live(generate_data_table(force, absolute_position, loadcell_limit, force_offset), refresh_per_second=12, transient=True)
    
    with live_table:
        while mode == 0:            
            if my_loadcell.is_calibrated:
                while my_loadcell.is_batch_ready(batch_index, batch_size):                
                    batch, batch_index = my_loadcell.get_batch(batch_index, batch_size)
                    force = mean(batch['F'])
            else:
                force = None

            if my_controller.is_calibrated:
                try:
                    absolute_position = my_controller.get_absolute_position()
                except:
                    absolute_position = None
            else:
                absolute_position = None

            live_table.update(generate_data_table(force, absolute_position, loadcell_limit, force_offset))

            if down_button.is_active and my_controller._down_endstop.is_active:
                my_controller.motor_stop()
            if up_button.is_active and my_controller._up_endstop.is_active:
                my_controller.motor_stop()

    if my_loadcell.is_calibrated:
        my_loadcell.stop_reading()
    
    mode_button.when_released = None
    up_button.when_pressed = None
    up_button.when_released = None
    down_button.when_pressed = None
    down_button.when_released = None
    
    utility.delete_last_lines(printed_lines)
    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for manual mode to be stopped...', '[green]:heavy_check_mark:[/green]')
    
    return

def save_test_parameters(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, output_dir:str):
    if my_loadcell.is_calibrated:
        calibration = my_loadcell.get_calibration()
        test_parameters['calibration'] = calibration
        test_parameters['loadcell_type'] = '{} {}'.format(calibration['loadcell_limit']['value'], calibration['loadcell_limit']['unit'])
    
    if my_controller.is_calibrated:
        if test_parameters['test_type'] == 'monotonic' or test_parameters['test_type'] == 'cyclic':
            test_parameters['initial_gauge_length'] = {
                'value': test_parameters['clamps_distance']['value'] + my_controller.get_absolute_position(),
                'unit': 'mm'
            }

    filename = 'test_parameters.json'
    with open(os.path.join(output_dir, filename), 'w') as f:
        json.dump(test_parameters, f)

    return

def postprocess_data(data, test_parameters:dict, filter_kernel_size:int = 21):
    cross_section = test_parameters['cross_section']['value']
    initial_gauge_length = test_parameters['initial_gauge_length']['value']

    def _postprocess_single_dataframe(df, t0):
        # Compute time
        df['t'] = df['t'] - t0

        # Add raw columns
        df['F_raw'] = df['F']
        df['stress_raw'] = df['F_raw'] / cross_section

        # Drop replaced columns
        df.drop(columns='F', inplace=True)

        # Add filtered columns
        df['F_med' + str(filter_kernel_size)] = scipy.signal.medfilt(df['F_raw'], filter_kernel_size)
        df['stress_med' + str(filter_kernel_size)] = df['F_med' + str(filter_kernel_size)] / cross_section

        # Add other meaningful data
        df.loc[df.index[0], 'cross_section'] = cross_section
        df.loc[df.index[0], 'initial_gauge_length'] = initial_gauge_length

        return df

    if isinstance(data, list):
        data_list = data
        t0 = data_list[0]['t'][0]

        for _data in data_list:
            _data = _postprocess_single_dataframe(_data, t0)
        
        data = data_list
    else:
        t0 = data['t'][0]
        data = _postprocess_single_dataframe(data, t0)

    return data