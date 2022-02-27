from rich import box
from rich.table import Table
from src import constants

def _parse_value(value:float, ndigits:int = None):
    if value is None:
        value = '-'
    elif ndigits is not None:
        value = round(value, ndigits)

    return value

def _get_loadcell_usage(force:float, loadcell_limit:float, force_offset:float):
    if (force is None) or (loadcell_limit is None):
        loadcell_usage = '-'
        loadcell_usage_style = None
    else:
        if force_offset is None:
            force_offset = 0
        
        loadcell_usage = abs(round(((force + force_offset) / loadcell_limit) * 100, 2))
        loadcell_usage_style = 'red' if loadcell_usage > 85 else None

    return loadcell_usage, loadcell_usage_style

def _get_initial_position(test_parameters:dict):
    initial_position = test_parameters['initial_gauge_length']['value'] - test_parameters['clamps_distance']['value']

    return initial_position

def _get_test_progress(test_parameters:dict, absolute_position:float):
    # TODO: add test progress computation for cyclic tests
    if absolute_position is None:
        test_progress = None
    else:
        initial_position = _get_initial_position(test_parameters)
        test_progress = ((absolute_position - initial_position) / test_parameters['displacement']['value']) * 100

    test_progress = _parse_value(test_progress, ndigits=constants.N_DIGITS_PROGRESS)

    return test_progress

def _generate_cyclic_data_table(test_parameters:dict, force:float, absolute_position:float, loadcell_limit:float, force_offset:float):
    loadcell_usage, loadcell_usage_style = _get_loadcell_usage(force, loadcell_limit, force_offset)
    # TODO: add cyclic test progress
    force = _parse_value(force, ndigits=constants.N_DIGITS_FORCE)
    absolute_position = _parse_value(absolute_position, ndigits=constants.N_DIGITS_POSITION)

    table = Table(box=box.ROUNDED)
    table.add_column('Force', justify='center', min_width=12)
    table.add_column('Absolute position', justify='center', min_width=20)
    table.add_column('Load Cell usage', justify='center', min_width=12, style=loadcell_usage_style)
    
    table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %')

    return table

def _generate_manual_data_table(force:float, absolute_position:float, loadcell_limit:float, force_offset:float):
    loadcell_usage, loadcell_usage_style = _get_loadcell_usage(force, loadcell_limit, force_offset)
    force = _parse_value(force, ndigits=constants.N_DIGITS_FORCE)
    absolute_position = _parse_value(absolute_position, ndigits=constants.N_DIGITS_POSITION)

    table = Table(box=box.ROUNDED)
    table.add_column('Force', justify='center', min_width=12)
    table.add_column('Absolute position', justify='center', min_width=20)
    table.add_column('Load Cell usage', justify='center', min_width=12, style=loadcell_usage_style)

    table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %')

    return table

def _generate_monotonic_data_table(test_parameters:dict, force:float, absolute_position:float, loadcell_limit:float, force_offset:float):
    loadcell_usage, loadcell_usage_style = _get_loadcell_usage(force, loadcell_limit, force_offset)
    test_progress = _get_test_progress(test_parameters, absolute_position)
    force = _parse_value(force, ndigits=constants.N_DIGITS_FORCE)
    absolute_position = _parse_value(absolute_position, ndigits=constants.N_DIGITS_POSITION)

    table = Table(box=box.ROUNDED)
    table.add_column('Force', justify='center', min_width=12)
    table.add_column('Absolute position', justify='center', min_width=20)
    table.add_column('Load Cell usage', justify='center', min_width=12, style=loadcell_usage_style)
    table.add_column('Test progress', justify='center', min_width=12)        
    
    table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %', f'{test_progress} %')

    return table

def generate_data_table(force:float, absolute_position:float, loadcell_limit:float, force_offset:float, test_parameters:dict = None):
    if test_parameters is None:
        table = _generate_manual_data_table(force, absolute_position, loadcell_limit, force_offset)
    elif test_parameters['test_type'] == 'monotonic':
        table = _generate_monotonic_data_table(test_parameters, force, absolute_position, loadcell_limit, force_offset)
    elif test_parameters['test_type'] == 'cyclic':
        table = _generate_cyclic_data_table(test_parameters, force, absolute_position, loadcell_limit, force_offset)
    else:
        # TODO: add static data table
        table = None
    
    return table