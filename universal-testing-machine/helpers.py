import os
from statistics import mean
from InquirerPy import inquirer, validator
from rich import box
from rich.console import Console
from rich.table import Table
from rich.live import Live
console = Console()
from datetime import datetime
from utility import utility
from controller import controller
from loadcell import loadcell
import json
import scipy.signal
from gpiozero import Button
import constants
import time
import pyqtgraph as pg
from pyqtgraph.functions import mkPen
import pandas as pd

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

def _generate_data_table(force:float, absolute_position:float, loadcell_limit:float, force_offset:float, test_parameters:dict = None):
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

    live_table = Live(_generate_data_table(force, absolute_position, loadcell_limit, force_offset), refresh_per_second=12, transient=True)
    
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

            live_table.update(_generate_data_table(force, absolute_position, loadcell_limit, force_offset))

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

def _read_monotonic_test_parameters():
    test_parameters = {}

    test_parameters['cross_section'] = {
        'value': float(
            inquirer.text(
                message='Insert the sample cross section [mm²]:',
                validate=validator.NumberValidator(float_allowed=True)
            ).execute()
        ),
        'unit': 'mm²'
    }

    test_parameters['clamps_distance'] = {
        'value': float(
            inquirer.text(
                message='Insert the clamps distance [mm]:',
                validate=validator.NumberValidator(float_allowed=True),
                default=str(constants.DEFAULT_CLAMPS_DISTANCE)
            ).execute()
        ),
        'unit': 'mm'
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

    return test_parameters

def _read_cyclic_test_parameters():
    test_parameters = {}

    test_parameters['cross_section'] = {
        'value': float(
            inquirer.text(
                message='Insert the sample cross section [mm²]:',
                validate=validator.NumberValidator(float_allowed=True)
            ).execute()
        ),
        'unit': 'mm²'
    }

    test_parameters['clamps_distance'] = {
        'value': float(
            inquirer.text(
                message='Insert the clamps distance [mm]:',
                validate=validator.NumberValidator(float_allowed=True),
                default=str(constants.DEFAULT_CLAMPS_DISTANCE)
            ).execute()
        ),
        'unit': 'mm'
    }

    test_parameters['cycles_number'] = float(
        inquirer.text(
            message='Insert the number of cycles to execute:',
            validate=validator.NumberValidator(float_allowed=False)
        ).execute()
    )

    # CYCLIC PHASE PARAMETERS
    cyclic_phase_parameters = {}

    cyclic_phase_parameters['cyclic_upper_limit'] = {
        'value': float(
            inquirer.text(
                message='Insert the cycle upper limit as a displacement with respect to the current position [mm]:',
                validate=validator.NumberValidator(float_allowed=True)
            ).execute()
        ),
        'unit': 'mm'
    }

    cyclic_phase_parameters['cyclic_lower_limit'] = {
        'value': float(
            inquirer.text(
                message='Insert the cycle lower limit as a displacement with respect to the current position [mm]:',
                validate=validator.NumberValidator(float_allowed=True),
                default=str(0)
            ).execute()
        ),
        'unit': 'mm'
    }

    cyclic_phase_parameters['cyclic_speed'] = {
        'value': float(
            inquirer.text(
                message='Insert the speed to employ during each load cycle [mm/s]:',
                validate=validator.NumberValidator(float_allowed=True)
            ).execute()
        ),
        'unit': 'mm/s'
    }

    cyclic_phase_parameters['cyclic_return_speed'] = {
        'value': float(
            inquirer.text(
                message='Insert the speed to employ during each unload cycle [mm/s]:',
                validate=validator.NumberValidator(float_allowed=True),
                default=str(cyclic_phase_parameters['cyclic_speed']['value'])
            ).execute()
        ),
        'unit': 'mm/s'
    }

    cyclic_phase_parameters['cyclic_delay'] = {
        'value': float(
            inquirer.text(
                message='Insert the delay before starting a new load cycle [s]:',
                validate=validator.NumberValidator(float_allowed=True),
                default=str(0)
            ).execute()
        ),
        'unit': 's'
    }

    cyclic_phase_parameters['cyclic_return_delay'] = {
        'value': float(
            inquirer.text(
                message='Insert the delay before unloading the specimen [s]:',
                validate=validator.NumberValidator(float_allowed=True),
                default=str(0)
            ).execute()
        ),
        'unit': 's'
    }

    test_parameters = {**test_parameters, **cyclic_phase_parameters}

    # PRETENSIONING PHASE PARAMETERS
    pretensioning_phase_parameters = {}

    pretensioning_phase_parameters['is_pretensioning_set'] = inquirer.confirm(
        message='Do you want to perform a pretensioning cycle?'
    ).execute()

    if pretensioning_phase_parameters['is_pretensioning_set'] is True:
        pretensioning_phase_parameters['pretensioning_speed'] = {
            'value': float(
                inquirer.text(
                    message='Insert the speed to employ during each load cycle [mm/s]:',
                    validate=validator.NumberValidator(float_allowed=True),
                    default=str(cyclic_phase_parameters['cyclic_speed']['value'])
                ).execute()
            ),
            'unit': 'mm/s'
        }

        pretensioning_phase_parameters['pretensioning_return_speed'] = {
            'value': float(
                inquirer.text(
                    message='Insert the speed to employ during each unload cycle [mm/s]:',
                    validate=validator.NumberValidator(float_allowed=True),
                    default=str(cyclic_phase_parameters['cyclic_return_speed']['value'])
                ).execute()
            ),
            'unit': 'mm/s'
        }

        pretensioning_phase_parameters['pretensioning_return_delay'] = {
            'value': float(
                inquirer.text(
                    message='Insert the delay before unloading the specimen during the pretensioning [s]:',
                    validate=validator.NumberValidator(float_allowed=True),
                    default=str(cyclic_phase_parameters['cyclic_return_delay']['value'])
                ).execute()
            ),
            'unit': 's'
        }

        pretensioning_phase_parameters['pretensioning_after_delay'] = {
            'value': float(
                inquirer.text(
                    message='Insert the delay before starting the cyclic phase [s]:',
                    validate=validator.NumberValidator(float_allowed=True),
                    default=str(0)
                ).execute()
            ),
            'unit': 's'
        }

    test_parameters = {**test_parameters, **pretensioning_phase_parameters}

    # FAILURE PHASE PARAMETERS
    failure_phase_parameters = {}

    failure_phase_parameters['is_failure_set'] = inquirer.confirm(
        message='Do you want the test to finish by reaching specimen failure?'
    ).execute()

    if failure_phase_parameters['is_failure_set'] is True:
        failure_phase_parameters['failure_speed'] = {
            'value': float(
                inquirer.text(
                    message='Insert the speed to employ while reaching failure [mm/s]:',
                    validate=validator.NumberValidator(float_allowed=True),
                    default=str(cyclic_phase_parameters['cyclic_speed']['value'])
                ).execute()
            ),
            'unit': 'mm/s'
        }

        failure_phase_parameters['failure_before_delay'] = {
            'value': float(
                inquirer.text(
                    message='Insert the delay before starting the failure phase [s]:',
                    validate=validator.NumberValidator(float_allowed=True),
                    default=str(0)
                ).execute()
            ),
            'unit': 's'
        }

    test_parameters = {**test_parameters, **failure_phase_parameters}

    return test_parameters

def read_test_parameters(test_type:bool):
    is_confirmed = False

    timestamp = datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
    test_parameters = {
        'test_id': timestamp,
        'test_type': test_type,
        'date': timestamp
    }

    while not is_confirmed:
        if test_type == 'monotonic':
            monotonic_test_parameters = _read_monotonic_test_parameters()
            test_parameters = {**test_parameters, **monotonic_test_parameters}
        elif test_type == 'cyclic':
            cyclic_test_parameters = _read_cyclic_test_parameters()
            test_parameters = {**test_parameters, **cyclic_test_parameters}
        elif test_type == 'static':
            pass

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
    
    if my_controller.is_calibrated:
        if test_parameters['test_type'] == 'monotonic' or test_parameters['test_type'] == 'cyclic':
            test_parameters['initial_gauge_length'] = {
                'value': test_parameters['clamps_distance']['value'] + my_controller.get_absolute_position(),
                'unit': 'mm'
            }

    filename = 'test_parameters.json'
    with open(output_dir + r'/' + filename, 'w') as f:
        json.dump(test_parameters, f)

    return

def _postprocess_data(data, test_parameters:dict, filter_kernel_size:int = 21):
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

def _run_go(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, plot_item, plot_color, speed, displacement, direction, stop_flag, stop_button, initial_absolute_position, reference_absolute_position, test_parameters):
    data = None

    if stop_flag is False:
        initial_gauge_length = test_parameters['initial_gauge_length']['value']
        loadcell_limit = my_loadcell.get_calibration()['loadcell_limit']['value']

        stop_flag = stop_flag
        def _switch_stop_flag():
            nonlocal stop_flag
            stop_flag = True
            return
        stop_button.when_released = lambda: _switch_stop_flag()
        
        plot_data = plot_item.plot(pen=None, symbol=constants.PLOTS_SYMBOL, symbolSize=constants.PLOTS_SYMBOL_SIZE)
        plot_data.opts['useCache'] = True
        plot_data.setSymbolPen(mkPen(plot_color))

        strains = []
        forces = []
        batch_index = 0

        live_table = Live(_generate_data_table(None, None, None, None), refresh_per_second=12, transient=True)

        my_loadcell.start_reading()
        _, _, t0 = my_controller.run(speed, displacement, direction)

        if direction == controller.DOWN:
            speed = -speed

        with live_table:
            while my_controller.is_running:
                if stop_flag:
                    my_controller.abort()
                else:
                    while my_loadcell.is_batch_ready(batch_index):
                        batch, batch_index = my_loadcell.get_batch(batch_index)
                        batch['t'] = batch['t'] - t0
                        batch['strain'] = ((batch['t'] * speed + reference_absolute_position - initial_absolute_position) / initial_gauge_length) * 100

                        forces.extend(batch['F'])
                        strains.extend(batch['strain'])

                        plot_data.setData(strains, forces)

                        pg.Qt.QtGui.QApplication.processEvents()
                    else:
                        pass
                        
                    live_table.update(
                        _generate_data_table(
                            force=forces[-1] if len(forces) > 0 else None, 
                            absolute_position=(initial_absolute_position + (strains[-1] * initial_gauge_length / 100)) if len(strains) > 0 else None,
                            loadcell_limit=loadcell_limit,
                            force_offset=my_loadcell.get_offset(is_force=True),
                            test_parameters=test_parameters
                        )
                    )

        data = my_loadcell.stop_reading()

        stop_button.when_released = None

        # DERIVED DATA COMPUTATION
        t0 = data['t'][0]
        data['displacement'] = (data['t'] - t0) * speed + (reference_absolute_position - initial_absolute_position)
        data['strain'] = (data['displacement'] / test_parameters['initial_gauge_length']['value']) * 100

    return data, stop_flag

def _run_delay(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, plot_item, plot_color, delay, stop_flag, stop_button, initial_absolute_position, test_parameters):
    data = None

    if stop_flag is False and delay != 0:
        initial_gauge_length = test_parameters['initial_gauge_length']['value']
        loadcell_limit = my_loadcell.get_calibration()['loadcell_limit']['value']

        stop_flag = stop_flag
        def _switch_stop_flag():
            nonlocal stop_flag
            stop_flag = True
            return
        stop_button.when_released = lambda: _switch_stop_flag()
        
        plot_data = plot_item.plot(pen=None, symbol=constants.PLOTS_SYMBOL, symbolSize=constants.PLOTS_SYMBOL_SIZE)
        plot_data.opts['useCache'] = True
        plot_data.setSymbolPen(mkPen(plot_color))

        strains = []
        forces = []
        batch_index = 0

        fixed_strain = ((my_controller.get_absolute_position() - initial_absolute_position) / initial_gauge_length) * 100

        live_table = Live(_generate_data_table(None, None, None, None), refresh_per_second=12, transient=True)

        my_loadcell.start_reading()
        t0 = my_controller.hold_torque()

        with live_table:
            while my_controller.is_holding:
                if stop_flag or time.time() - t0 >= delay:
                    my_controller.release_torque()
                else:
                    while my_loadcell.is_batch_ready(batch_index):
                        batch, batch_index = my_loadcell.get_batch(batch_index)
                        batch['t'] = batch['t'] - t0
                        batch['strain'] = fixed_strain

                        forces.extend(batch['F'])
                        strains.extend(batch['strain'])

                        plot_data.setData(strains, forces)

                        pg.Qt.QtGui.QApplication.processEvents()
                    else:
                        pass
                        
                    live_table.update(
                        _generate_data_table(
                            force=forces[-1] if len(forces) > 0 else None, 
                            absolute_position=(initial_absolute_position + (strains[-1] * initial_gauge_length / 100)) if len(strains) > 0 else None,
                            loadcell_limit=loadcell_limit,
                            force_offset=my_loadcell.get_offset(is_force=True),
                            test_parameters=test_parameters
                        )
                    )

        data = my_loadcell.stop_reading()

        stop_button.when_released = None

        # DERIVED DATA COMPUTATION
        data['displacement'] = fixed_strain * initial_gauge_length / 100
        data['strain'] = fixed_strain

    return data, stop_flag

def _start_monotonic_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, stop_button_pin:int):
    console.print('[#e5c07b]>[/#e5c07b]', 'Collecting data...')
    printed_lines = 1
    
    displacement = test_parameters['displacement']['value']
    linear_speed = test_parameters['linear_speed']['value']
    cross_section = test_parameters['cross_section']['value']
    initial_gauge_length = test_parameters['initial_gauge_length']['value']
    initial_absolute_position = my_controller.get_absolute_position()
    loadcell_limit = my_loadcell.get_calibration()['loadcell_limit']['value']

    stop_flag = False
    stop_button = Button(pin=stop_button_pin)

    plot_widget = pg.plot(title='Monotonic Test Plot')
    plot_widget.setMouseEnabled(x=False, y=False)
    plot_item = plot_widget.getPlotItem()

    xlim = round((displacement / initial_gauge_length) * 1.1 * 100) # 10% margin
    ylim = loadcell_limit
    plot_item.getViewBox().setRange(xRange=(0, xlim), yRange=(0, ylim))
    plot_item.setLabel('bottom', 'Strain', '%')
    plot_item.setLabel('left', 'Force', 'N')
    plot_item.setTitle('Force vs. Strain')

    data, stop_flag = _run_go(
        my_controller,
        my_loadcell,
        plot_item=plot_item,
        plot_color='#FFFFFF',
        speed=linear_speed,
        displacement=displacement,
        direction=controller.UP,
        stop_flag=stop_flag,
        stop_button=stop_button,
        initial_absolute_position=initial_absolute_position,
        reference_absolute_position=initial_absolute_position,
        test_parameters=test_parameters
    )

    utility.delete_last_lines(printed_lines)
    console.print('[#e5c07b]>[/#e5c07b]', 'Collecting data...', '[green]:heavy_check_mark:[/green]')

    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for the plot figure to be closed...')       
    pg.exec()
    utility.delete_last_lines(n_lines=1)
    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for the plot figure to be closed...', '[green]:heavy_check_mark:[/green]')   

    return data

def _start_cyclic_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, stop_button_pin:int):
    console.print('[#e5c07b]>[/#e5c07b]', 'Collecting data...')
    printed_lines = 1
    
    # GENERIC PARAMETERS
    cycles_number = test_parameters['cycles_number']
    cross_section = test_parameters['cross_section']['value']
    initial_gauge_length = test_parameters['initial_gauge_length']['value']
    initial_absolute_position = my_controller.get_absolute_position()
    loadcell_limit = my_loadcell.get_calibration()['loadcell_limit']['value']

    # CYCLIC PHASE PARAMETERS
    cyclic_upper_limit = test_parameters['cyclic_upper_limit']['value']
    cyclic_lower_limit = test_parameters['cyclic_lower_limit']['value']
    cyclic_speed = test_parameters['cyclic_speed']['value']
    cyclic_return_speed = test_parameters['cyclic_return_speed']['value']
    cyclic_delay = test_parameters['cyclic_delay']['value']
    cyclic_return_delay = test_parameters['cyclic_return_delay']['value']

    # PRETENSIONING PHASE PARAMETERS
    is_pretensioning_set = test_parameters['is_pretensioning_set']
    if is_pretensioning_set:
        pretensioning_speed = test_parameters['pretensioning_speed']['value']
        pretensioning_return_speed = test_parameters['pretensioning_return_speed']['value']
        pretensioning_return_delay = test_parameters['pretensioning_return_delay']['value']
        pretensioning_after_delay = test_parameters['pretensioning_after_delay']['value']

    # FAILURE PHASE PARAMETERS
    is_failure_set = test_parameters['is_failure_set']
    if is_failure_set:
        failure_speed = test_parameters['failure_speed']['value']
        failure_before_delay = test_parameters['failure_before_delay']['value']

    stop_flag = False
    stop_button = Button(pin=stop_button_pin)

    plot_widget = pg.plot(title='Cyclic Test Plot')
    plot_widget.setMouseEnabled(x=False, y=False)
    plot_item = plot_widget.getPlotItem()

    xlim = round((cyclic_upper_limit / initial_gauge_length) * 1.1 * 100) # 10% margin
    ylim = loadcell_limit
    plot_item.getViewBox().setRange(xRange=(0, xlim), yRange=(0, ylim))
    plot_item.setLabel('bottom', 'Strain', '%')
    plot_item.setLabel('left', 'Force', 'N')
    plot_item.setTitle('Force vs. Strain')

    data_list = []
    data_labels_list = []
    
    if is_pretensioning_set:
        # PRETENSIONING PHASE - GO
        reference_absolute_position = initial_absolute_position
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#FF0000',
            speed=pretensioning_speed,
            displacement=(cyclic_upper_limit + initial_absolute_position) - reference_absolute_position,
            direction=controller.UP,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            reference_absolute_position=reference_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('pretensioning_go')

        # PRETENSIONING PHASE - RETURN DELAY
        data, stop_flag = _run_delay(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#00FF00',
            delay=pretensioning_return_delay,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('pretensioning_return_delay')

        # PRETENSIONING PHASE - RETURN
        reference_absolute_position = my_controller.get_absolute_position()
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#0000FF',
            speed=pretensioning_return_speed,
            displacement=reference_absolute_position - (initial_absolute_position + cyclic_lower_limit),
            direction=controller.DOWN,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            reference_absolute_position=reference_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('pretensioning_return')

        # PRETENSIONING PHASE - AFTER DELAY
        data, stop_flag = _run_delay(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#FFFF00',
            delay=pretensioning_after_delay,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('pretensioning_after_delay')

    # CYCLIC PHASE
    for cycle_idx in range(int(cycles_number)):
        # CYCLIC PHASE - GO
        reference_absolute_position = my_controller.get_absolute_position()
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#FF00FF',
            speed=cyclic_speed,
            displacement=(cyclic_upper_limit + initial_absolute_position) - reference_absolute_position,
            direction=controller.UP,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            reference_absolute_position=reference_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('cycle_' + str(cycle_idx) + '_go')
    
        # CYCLIC PHASE - RETURN DELAY
        data, stop_flag = _run_delay(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#00FF00',
            delay=cyclic_return_delay,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('cycle_' + str(cycle_idx) + '_return_delay')

        # CYCLIC PHASE - RETURN
        reference_absolute_position = my_controller.get_absolute_position()
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#00FFFF',
            speed=cyclic_return_speed,
            displacement=reference_absolute_position - (initial_absolute_position + cyclic_lower_limit),
            direction=controller.DOWN,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            reference_absolute_position=reference_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('cycle_' + str(cycle_idx) + '_return')
        
        # CYCLIC PHASE - DELAY
        if cycle_idx < (int(cycles_number) - 1):
            data, stop_flag = _run_delay(
                my_controller,
                my_loadcell,
                plot_item=plot_item,
                plot_color='#00FF00',
                delay=cyclic_delay,
                stop_flag=stop_flag,
                stop_button=stop_button,
                initial_absolute_position=initial_absolute_position,
                test_parameters=test_parameters
            )
            if data is not None:
                data_list.append(data)
                data_labels_list.append('cycle_' + str(cycle_idx) + '_delay')

    # FAILURE PHASE
    if is_failure_set:
        plot_item.getViewBox().enableAutoRange(axis='x')

        # FAILURE PHASE - BEFORE DELAY
        data, stop_flag = _run_delay(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#F0F0F0',
            delay=failure_before_delay,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('failure_before_delay')

        # FAILURE PHASE - GO
        reference_absolute_position = my_controller.get_absolute_position()
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color='#0F0F0F',
            speed=failure_speed,
            displacement=150,
            direction=controller.UP,
            stop_flag=stop_flag,
            stop_button=stop_button,
            initial_absolute_position=initial_absolute_position,
            reference_absolute_position=reference_absolute_position,
            test_parameters=test_parameters
        )
        if data is not None:
            data_list.append(data)
            data_labels_list.append('failure_go')
    
    utility.delete_last_lines(printed_lines)
    console.print('[#e5c07b]>[/#e5c07b]', 'Collecting data...', '[green]:heavy_check_mark:[/green]')

    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for the plot figure to be closed...')       
    pg.exec()
    utility.delete_last_lines(n_lines=1)
    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for the plot figure to be closed...', '[green]:heavy_check_mark:[/green]') 

    return data_list, data_labels_list

def _start_static_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, stop_button_pin:int):
    console.print('[#e5c07b]>[/#e5c07b]', 'Collecting data...')
    printed_lines = 1

    loadcell_limit = my_loadcell.get_calibration()['loadcell_limit']['value']
    
    stop_flag = False
    def _switch_stop_flag():
        nonlocal stop_flag
        stop_flag = True
        return

    stop_button = Button(pin=stop_button_pin)
    stop_button.when_released = lambda: _switch_stop_flag()

    plot_widget = pg.plot(title='Static Test Plot')
    plot_widget.setMouseEnabled(x=False, y=False)
    plot_item = plot_widget.getPlotItem()

    xlim = 30 # in seconds
    ylim = loadcell_limit
    plot_item.getViewBox().setRange(xRange=(0, xlim), yRange=(0, ylim))
    plot_item.setLabel('bottom', 'Time', 's')
    plot_item.setLabel('left', 'Force', 'N')
    plot_item.setTitle('Force vs. Time')

    plot_data = plot_item.plot(pen=None, symbol=constants.PLOTS_SYMBOL, symbolSize=constants.PLOTS_SYMBOL_SIZE)
    plot_data.opts['useCache'] = True
    plot_data.setSymbolPen(mkPen('#FFFFFF'))

    timings = []
    forces = []
    batch_index = 0

    live_table = Live(_generate_data_table(None, None, None, None), refresh_per_second=12, transient=True)

    t0 = my_controller.hold_torque()
    my_loadcell.start_reading()

    with live_table:
        while my_controller.is_holding:
            if stop_flag:
                my_controller.release_torque()
            else:
                while my_loadcell.is_batch_ready(batch_index):
                    batch, batch_index = my_loadcell.get_batch(batch_index)
                    batch['t'] = batch['t'] - t0

                    forces.extend(batch['F'])
                    timings.extend(batch['t'])

                    if batch['t'].iloc[-1] > xlim:
                        new_xlim = (xlim / 2) + batch['t'].iloc[-1]
                        plot_item.getViewBox().setXRange((xlim / 2), new_xlim)
                        xlim = new_xlim

                    plot_data.setData(timings, forces)

                    pg.Qt.QtGui.QApplication.processEvents()
                else:
                    pass

                live_table.update(
                    _generate_data_table(
                        force=forces[-1] if len(forces) > 0 else None,
                        absolute_position=None,
                        loadcell_limit=loadcell_limit,
                        force_offset=my_loadcell.get_offset(is_force=True)
                    )
                )

    utility.delete_last_lines(printed_lines)
    console.print('[#e5c07b]>[/#e5c07b]', 'Collecting data...', '[green]:heavy_check_mark:[/green]')

    data = my_loadcell.stop_reading()
    stop_button.when_released = None

    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for the plot figure to be closed...')       
    pg.exec()
    utility.delete_last_lines(n_lines=1)
    console.print('[#e5c07b]>[/#e5c07b]', 'Waiting for the plot figure to be closed...', '[green]:heavy_check_mark:[/green]')   

    data['t'] = data['t'] - t0
    data['F_raw'] = data['F']
    data['F_med20'] = scipy.signal.medfilt(data['F'], 21)

    return data

def start_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, output_dir:str, stop_button_pin:int):
    data = None
    data_labels = None

    if test_parameters['test_type'] == 'monotonic':
        data = _start_monotonic_test(
            my_controller=my_controller,
            my_loadcell=my_loadcell,
            test_parameters=test_parameters,
            stop_button_pin=stop_button_pin
        )
    elif test_parameters['test_type'] == 'cyclic':
        data, data_labels = _start_cyclic_test(
            my_controller=my_controller,
            my_loadcell=my_loadcell,
            test_parameters=test_parameters,
            stop_button_pin=stop_button_pin
        )
    elif test_parameters['test_type'] == 'static':
        data = _start_static_test(
            my_controller=my_controller,
            my_loadcell=my_loadcell,
            stop_button_pin=stop_button_pin
        )

    with console.status('Postprocessing test data...'):
        if data is not None:
            data = _postprocess_data(data, test_parameters)
    
    console.print('[#e5c07b]>[/#e5c07b]', 'Postprocessing test data...', '[green]:heavy_check_mark:[/green]')

    with console.status('Saving test data...'):
        # Save .xlsx file
        filename = test_parameters['test_id'] + '.xlsx'
        if data is not None:
            writer = pd.ExcelWriter(output_dir + r'/' + filename)
            
            if isinstance(data, list):
                data_list = data
                for idx, _ in enumerate(data_list):
                    data_list[idx].to_excel(writer, sheet_name=data_labels[idx], index=False)
            else:
                data.to_excel(writer, sheet_name=test_parameters['test_id'], index=False)
            
            writer.save()
        
        # Save complete .csv file
        filename = test_parameters['test_id'] + '.csv'
        if data is not None:
            if isinstance(data, list):
                data = pd.concat(data, ignore_index=True)

            data.to_csv(output_dir + r'/' + filename, index=False)

    console.print('[#e5c07b]>[/#e5c07b]', 'Saving test data...', '[green]:heavy_check_mark:[/green]')
    
    return