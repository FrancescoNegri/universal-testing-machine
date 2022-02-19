import os
import json
from InquirerPy import inquirer, validator
from src import constants
from datetime import datetime
from rich.console import Console
console = Console()

def _create_configurations_dir():
    dir = os.path.dirname(__package__)
    path = './.configurations'
    configurations_dir = os.path.join(dir, path)
    os.makedirs(configurations_dir, exist_ok=True)

    return configurations_dir


def _list_configurations(configurations_dir: str):
    configurations = []
    for f in os.listdir(configurations_dir):
        if os.path.isfile(os.path.join(configurations_dir, f)):
            configurations.append(f)

    return configurations


def _load_configuration(configurations_dir: str, configuration_name: str, test_type: str):
    try:
        with open(os.path.join(configurations_dir, configuration_name)) as f:
            test_parameters = json.load(f)
            if test_parameters['test_type'] == test_type:
                # TODO: check all parameters are ok
                console.print('[#e5c07b]>[/#e5c07b]', 'Test parameters loaded correctly.')
                console.print_json(json.dumps(test_parameters))
            else:
                console.print('[#e5c07b]![/#e5c07b]', 'The loaded set of parameters is for another type of test.')
                console.print('[#e5c07b]![/#e5c07b]', 'Expected: [bold]{}[/bold] | Received: [bold]{}[/bold]'.format(test_type, test_parameters['test_type']))
                console.print('[#e5c07b]![/#e5c07b]', 'Retry.')
                test_parameters = None
    except:
        console.print('[#e5c07b]![/#e5c07b]', 'The selected set of test parameters could not be loaded. Retry.')
        test_parameters = None
    finally:
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
                    default=str(
                        cyclic_phase_parameters['cyclic_speed']['value'])
                ).execute()
            ),
            'unit': 'mm/s'
        }

        pretensioning_phase_parameters['pretensioning_return_speed'] = {
            'value': float(
                inquirer.text(
                    message='Insert the speed to employ during each unload cycle [mm/s]:',
                    validate=validator.NumberValidator(float_allowed=True),
                    default=str(
                        cyclic_phase_parameters['cyclic_return_speed']['value'])
                ).execute()
            ),
            'unit': 'mm/s'
        }

        pretensioning_phase_parameters['pretensioning_return_delay'] = {
            'value': float(
                inquirer.text(
                    message='Insert the delay before unloading the specimen during the pretensioning [s]:',
                    validate=validator.NumberValidator(float_allowed=True),
                    default=str(
                        cyclic_phase_parameters['cyclic_return_delay']['value'])
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
                    default=str(
                        cyclic_phase_parameters['cyclic_speed']['value'])
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


def _read_test_parameters(test_type: bool):

    timestamp = datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
    test_parameters = {
        'test_id': timestamp,
        'test_type': test_type,
        'date': timestamp
    }

    if test_type == 'monotonic':
        monotonic_test_parameters = _read_monotonic_test_parameters()
        test_parameters = {**test_parameters, **monotonic_test_parameters}
    elif test_type == 'cyclic':
        cyclic_test_parameters = _read_cyclic_test_parameters()
        test_parameters = {**test_parameters, **cyclic_test_parameters}
    elif test_type == 'static':
        pass

    return test_parameters


def _save_configuration(configurations_dir: str, test_parameters: dict):
    filename = inquirer.text(
        message='Insert a name for this configuration:',
        default=test_parameters['test_id']
    ).execute()

    test_parameters.pop('test_id', None)

    extension = '.json'
    filename = filename + extension

    # TODO: check if file already exists

    with open(os.path.join(configurations_dir, filename), 'w') as f:
        json.dump(test_parameters, f)

    return


def set_test_parameters(test_type: bool):
    is_confirmed = False

    while is_confirmed is False:
        test_parameters = None
        while test_parameters is None:
            configurations_dir = _create_configurations_dir()
            configurations = _list_configurations(configurations_dir)
            choices = ['Insert new test parameters']
            choices.extend(configurations)
            result = inquirer.fuzzy(
                message="Select an existing set of test parameters or insert new ones:",
                choices=choices
            ).execute()

            # Insert new test parameters
            if result == choices[0]:
                test_parameters = _read_test_parameters(test_type)

                result = inquirer.confirm(
                    message='Would you like to save this set of parameters as a new configuration?',
                    default=True
                ).execute()
                if result is True:
                    _save_configuration(configurations_dir, test_parameters)
            # Using an existing set of test parameters
            else:
                test_parameters = _load_configuration(configurations_dir, configuration_name=result, test_type=test_type)
                test_parameters['date'] = datetime.now().strftime('%Y_%m_%d-%H_%M_%S')

        test_parameters['test_id'] = inquirer.text(
            message='Insert the ID for this session:',
            validate=validator.EmptyInputValidator(),
            transformer=lambda result: ' '.join(
                result.split()).replace(' ', '_'),
            filter=lambda result: ' '.join(result.split()).replace(' ', '_'),
            default=test_parameters['date']
        ).execute()

        is_confirmed = inquirer.confirm(
            message='Confirm?'
        ).execute()
    return test_parameters
