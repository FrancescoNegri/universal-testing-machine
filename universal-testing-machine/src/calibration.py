import os
import json
import numbers
from datetime import datetime
from loadcell import loadcell
from controller import controller
from src import constants, helpers
from InquirerPy import inquirer, validator
from rich.console import Console
console = Console()

def calibrate_controller(my_controller:controller.LinearController):
    with console.status('Calibrating the crossbar...'):
        is_calibrated = my_controller.calibrate(speed=0.75, direction=controller.DOWN, is_linear=False)
    
    if is_calibrated:
        console.print('[#e5c07b]>[/#e5c07b]', 'Calibrating the crossbar...', '[green]:heavy_check_mark:[/green]')
    else:
        console.print('[#e5c07b]>[/#e5c07b]', 'Calibrating the crossbar...', '[red]:cross_mark:[/red]')
    
    return

def calibrate_loadcell(my_loadcell:loadcell.LoadCell):
    if my_loadcell.is_calibrated is True:
        console.print('[#e5c07b]>[/#e5c07b]', 'The loadcell is already calibrated.')
    else:
        is_confirmed = False

        while is_confirmed is False:
            calibration = None
            while calibration is None:
                calibration_dir = helpers.create_dir('./.calibration')
                calibrations = _list_loadcell_calibrations(calibration_dir)
                choices = ['New calibration']
                choices.extend(calibrations)
                result = inquirer.fuzzy(
                    message='Select an existing calibration or create a new one:',
                    choices=choices
                ).execute()

                # New calibration
                if result == choices[0]:
                    calibration = _read_loadcell_calibration(my_loadcell)

                    result = inquirer.confirm(
                        message='Would you like to save this calibration?',
                        default=True
                    ).execute()
                    if result is True:
                        _save_calibration(calibration_dir, calibration)
                # Existing calibration
                else:
                    calibration = _load_calibration(calibration_dir, calibration_name=result)
                    if calibration is not None:
                        calibration = my_loadcell.calibrate(calibration=calibration)
                
            is_confirmed = inquirer.confirm(
                message='Confirm?'
            ).execute()

    return

def _check_calibration(calibration:dict):
    is_ok = True

    required_keys = ['loadcell_limit', 'slope', 'y_intercept', 'calibrating_mass', 'date']

    if not set(required_keys).issubset(calibration.keys()):
        console.print('[#e5c07b]![/#e5c07b]', 'Missing required keys in the calibration.')
        is_ok = False
        return is_ok
    else:
        for key, value in calibration.items():
            if isinstance(value, dict):
                if not isinstance(value['value'], numbers.Number):
                    console.print('[#e5c07b]![/#e5c07b]', '[bold]{}.{}[/bold] field is not a number.'.format(key, 'value'))
                    is_ok = False
                    return is_ok
            else:
                if (not isinstance(value, numbers.Number)) and (key != 'date'):
                    console.print('[#e5c07b]![/#e5c07b]', '[bold]{}[/bold] field is not a number.'.format(key))
                    is_ok = False
                    return is_ok

    return is_ok

def _list_loadcell_calibrations(calibration_dir:str):
    calibrations = []
    for f in os.listdir(calibration_dir):
        if os.path.isfile(os.path.join(calibration_dir, f)):
            calibrations.append(f)
    
    return calibrations

def _load_calibration(calibration_dir:str, calibration_name:str):
    try:
        with open(os.path.join(calibration_dir, calibration_name)) as f:
            calibration = json.load(f)

            if _check_calibration(calibration) is True:
                console.print('[#e5c07b]>[/#e5c07b]', 'Calibration loaded correctly.')
                console.print_json(json.dumps(calibration))
            else:
                console.print('[#e5c07b]![/#e5c07b]', 'Calibration not loaded. Retry.')
                calibration = None
    except:
        console.print('[#e5c07b]![/#e5c07b]', 'The selected calibration could not be loaded. Retry.')
        calibration = None
    finally:
        return calibration

def _read_loadcell_calibration(my_loadcell:loadcell.LoadCell):
    loadcell_type = inquirer.select(
        message='Select the desired loadcell:',
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
    
    calibration = my_loadcell.calibrate(loadcell_limit=loadcell_type, zero_raw=zero_raw, mass_raw=mass_raw, calibrating_mass=calibrating_mass)

    return calibration

def _save_calibration(calibration_dir:str, calibration:dict):
    calibration['date'] = datetime.now().strftime('%Y_%m_%d-%H_%M_%S')

    filename = inquirer.text(
        message='Insert a name for this calibration:',
        default=calibration['date']
    ).execute()

    extension = '.json'

    if os.path.isfile(os.path.join(calibration_dir, filename + extension)):
        is_confirmed = inquirer.confirm(
            message='A calibration with the same name already exists. Overwrite it?'
        ).execute()

        if is_confirmed is False:
            copy_idx = ''
            idx = 0
            while os.path.isfile(os.path.join(calibration_dir, filename + copy_idx + extension)):
                idx = idx + 1
                copy_idx = '(' + str(idx) + ')'
            
            filename = filename + copy_idx
            console.print('[#e5c07b]>[/#e5c07b]', 'Calibration saved as: {}'.format(filename + extension))

    filename = filename + extension

    with open(os.path.join(calibration_dir, filename), 'w') as f:
        json.dump(calibration, f)

    return