import os
from statistics import mean
from InquirerPy import inquirer, validator
from rich import box
from rich.console import Console
from rich.table import Table
console = Console()
from datetime import datetime
from utility import utility
from controller import controller
from loadcell import loadcell
import json
import scipy.signal
from gpiozero import Button
import matplotlib.pyplot as plt

def create_calibration_dir():
    dir = os.path.dirname(__file__)
    path = '../.calibration'
    calibration_dir = os.path.join(dir, path)
    os.makedirs(calibration_dir, exist_ok=True)

    return calibration_dir

def create_output_dir(test_parameters:dict):
    dir = os.path.dirname(__file__)
    path = '../output'
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

def check_existing_calibration(calibration_dir:str, my_loadcell:loadcell.LoadCell):
    try:
        with open(calibration_dir + r'/' + my_loadcell._calibration_filename) as f:
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
            {'name': '63.352 g (1 N load cell)', 'value': 63.352},
            {'name': '361.606 g (10 N load cell)', 'value': 361.606},
            {'name': 'Custom', 'value': None}
        ],
        default= 361.606 if loadcell_type == 10 else 63.352
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

def _show_data_table(force, absolute_position, printed_lines:int):
    table = Table(box=box.ROUNDED)
    table.add_column('Force', justify='center', min_width=12)
    table.add_column('Absolute position', justify='center', min_width=20)
    table.add_row(f'{force} N', f'{absolute_position} mm')
    
    console.print(table)
    printed_lines += 5

    return printed_lines

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
    batch_index = 0
    batch_size = 25
    
    while mode == 0:
        if printed_lines > 1:
            utility.delete_last_lines(printed_lines - 1)
            printed_lines -= printed_lines - 1
        
        if my_loadcell.is_calibrated and force is not None:
            while my_loadcell.is_batch_ready(batch_index, batch_size):                
                batch, batch_index = my_loadcell.get_batch(batch_index, batch_size)
                force = round(mean(batch['F']), 5)
        else:
            force = '-'

        if my_controller.is_calibrated and absolute_position is not None:
            try:
                absolute_position = round(my_controller.get_absolute_position(), 2)
            except:
                absolute_position = '-'
        else:
            absolute_position = '-'

        printed_lines = _show_data_table(
            force=force,
            absolute_position=absolute_position,
            printed_lines=printed_lines
        )

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

def read_test_parameters(test_type:bool, default_clamps_distance:float = None):
    is_confirmed = False

    timestamp = datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
    test_parameters = {
        'test_id': timestamp,
        'test_type': test_type,
        'date': timestamp
    }

    while not is_confirmed:
        if test_type is 'monotonic':        
            test_parameters['cross_section'] = {
                'value': float(
                    inquirer.text(
                        message='Insert the sample cross section [mm²]:',
                        validate=validator.NumberValidator(float_allowed=True)
                    ).execute()
                ),
                'unit': 'mm²'
            }

            test_parameters['displacement'] = {
                'value': float(
                    inquirer.text(
                        message='Insert the desired displacement [mm]:',
                        validate=validator.NumberValidator(float_allowed=True)
                    ).execute()
                ),
                'unit': 'mm'
            }

            test_parameters['linear_speed'] = {
                'value': float(
                    inquirer.text(
                        message='Insert the desired linear speed [mm/s]:',
                        validate=validator.NumberValidator(float_allowed=True)
                    ).execute()
                ),
                'unit': 'mm/s'
            }

            test_parameters['clamps_distance'] = {
                'value': float(
                    inquirer.text(
                        message='Insert the clamps distance [mm]:',
                        validate=validator.NumberValidator(float_allowed=True),
                        default=str(default_clamps_distance)
                    ).execute()
                ),
                'unit': 'mm'
            }

        test_parameters['test_id'] = inquirer.text(
            message='Insert the ID for this session:',
            validate=validator.EmptyInputValidator(),
            transformer=lambda result: ' '.join(result.split()).replace(' ', '_'),
            filter=lambda result: ' '.join(result.split()).replace(' ', '_'),
            default=timestamp
        ).execute()

        is_confirmed = inquirer.confirm(
            message='Confirm?'
        ).execute()

    return test_parameters

def save_test_parameters(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, output_dir:str):
    if my_loadcell.is_calibrated:
        calibration = my_loadcell.get_calibration()
        test_parameters['calibration'] = calibration
        test_parameters['loadcell_type'] = '{} {}'.format(calibration['loadcell_limit']['value'], calibration['loadcell_limit']['unit'])
    
    if my_controller.is_calibrated and test_parameters['test_type'] is 'monotonic':
        test_parameters['initial_gauge_length'] = {
            'value': test_parameters['clamps_distance']['value'] + my_controller.get_absolute_position(),
            'unit': 'mm'
        }

    filename = 'test_parameters.json'
    with open(output_dir + r'/' + filename, 'w') as f:
        json.dump(test_parameters, f)

    return

def _start_monotonic_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, stop_button_pin:int):
    with console.status('Collecting data...'):
        displacement = test_parameters['displacement']['value']
        linear_speed = test_parameters['linear_speed']['value']
        cross_section = test_parameters['cross_section']['value']
        initial_gauge_length = test_parameters['initial_gauge_length']['value']

        stop_flag = False
        def _switch_stop_flag():
            nonlocal stop_flag
            stop_flag = True
            return

        stop_button = Button(pin=stop_button_pin)
        stop_button.when_released = lambda: _switch_stop_flag()

        strains = []
        forces = []
        batch_index = 0

        fig = plt.figure(facecolor='#DEDEDE')
        ax = plt.axes()
        line, = ax.plot(forces, strains, lw=3)

        xlim = round((displacement / initial_gauge_length) * 1.1 * 100) # 10% margin
        ylim = my_loadcell.get_calibration()['loadcell_limit']['value']
        ax.set_xlim([0, xlim])
        ax.set_ylim([0, ylim])
        ax.set_xlabel('Strain (%)')
        ax.set_ylabel('Force (N)')
        ax.set_title('Force vs. Strain')
        
        fig.canvas.draw()
        plt.show(block=False)

        _, _, t0 = my_controller.run(linear_speed, displacement, controller.UP)
        my_loadcell.start_reading()

        while my_controller.is_running:
            if stop_flag:
                my_controller.abort()
            else:
                while my_loadcell.is_batch_ready(batch_index):
                    batch, batch_index = my_loadcell.get_batch(batch_index)
                    batch['t'] = batch['t'] - t0
                    batch['strain'] = (batch['t'] * linear_speed / initial_gauge_length) * 100

                    forces.extend(batch['F'])
                    strains.extend(batch['strain'])

                    line.set_data(strains, forces)
                    ax.redraw_in_frame()
                    fig.canvas.blit(ax.bbox)
                    fig.canvas.flush_events()
                else:
                    pass

    console.print('[#e5c07b]>[/#e5c07b]', 'Collecting data...', '[green]:heavy_check_mark:[/green]')

    data = my_loadcell.stop_reading()
    stop_button.when_released = None

    data['t'] = data['t'] - t0
    data['displacement'] = data['t'] * linear_speed
    data['F_raw'] = data['F']
    data['F_med20'] = scipy.signal.medfilt(data['F'], 21)
    data['stress_raw'] = data['F_raw'] / cross_section
    data['stress_med20'] = data['F_med20'] / cross_section
    data['strain'] = (data['t'] * linear_speed / initial_gauge_length) * 100
    data.loc[data.index[0], 'cross_section'] = cross_section
    data.loc[data.index[0], 'initial_gauge_length'] = initial_gauge_length

    return data

def _start_static_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, stop_button_pin:int):
    with console.status('Collecting data...'):
        stop_flag = False
        def _switch_stop_flag():
            nonlocal stop_flag
            stop_flag = True
            return

        stop_button = Button(pin=stop_button_pin)
        stop_button.when_released = lambda: _switch_stop_flag()

        timings = []
        forces = []
        batch_index = 0

        fig = plt.figure(facecolor='#DEDEDE')
        ax = plt.axes()
        line, = ax.plot(timings, forces, lw=3)

        xlim = 30 # in seconds
        ylim = my_loadcell.get_calibration()['loadcell_limit']['value']
        ax.set_xlim([0, xlim])
        ax.set_ylim([0, ylim])
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Force (N)')
        ax.set_title('Force vs. Time')
        
        fig.canvas.draw()
        plt.show(block=False)

        t0 = my_controller.hold_torque()
        my_loadcell.start_reading()

        while my_controller.is_running:
            if stop_flag:
                my_controller.release_torque()
            else:
                while my_loadcell.is_batch_ready(batch_index):
                    batch, batch_index = my_loadcell.get_batch(batch_index)
                    batch['t'] = batch['t'] - t0

                    forces.extend(batch['F'])
                    timings.extend(batch['t'])

                    if batch['t'].iloc[-1] > xlim:
                        ax.set_xlim([(xlim / 2), (xlim / 2) + batch['t'].iloc[-1]])
                        xlim = (xlim / 2) + batch['t'].iloc[-1]

                    line.set_data(timings, forces)
                    ax.redraw_in_frame()
                    fig.canvas.blit(ax.bbox)
                    fig.canvas.flush_events()
                else:
                    pass

    console.print('[#e5c07b]>[/#e5c07b]', 'Collecting data...', '[green]:heavy_check_mark:[/green]')

    data = my_loadcell.stop_reading()
    stop_button.when_released = None

    data['t'] = data['t'] - t0
    data['F_raw'] = data['F']
    data['F_med20'] = scipy.signal.medfilt(data['F'], 21)

    return data

def start_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, output_dir:str, stop_button_pin:int):
    data = None

    if test_parameters['test_type'] is 'monotonic':
        data = _start_monotonic_test(
            my_controller=my_controller,
            my_loadcell=my_loadcell,
            test_parameters=test_parameters,
            stop_button_pin=stop_button_pin
        )
    elif test_parameters['test_type'] is 'cyclic':
        pass
    elif test_parameters['test_type'] is 'static':
        data = _start_static_test(
            my_controller=my_controller,
            my_loadcell=my_loadcell,
            stop_button_pin=stop_button_pin
        )

    with console.status('Saving test data...'):
        filename = test_parameters['test_id'] + '.csv'
        if data is not None:
            data.to_csv(output_dir + r'/' + filename, index=False)

    console.print('[#e5c07b]>[/#e5c07b]', 'Saving test data...', '[green]:heavy_check_mark:[/green]')
    
    return