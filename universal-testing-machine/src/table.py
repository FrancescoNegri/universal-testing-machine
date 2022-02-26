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

def generate_data_table(force:float, absolute_position:float, loadcell_limit:float, force_offset:float, test_parameters:dict = None):
    
    table = _generate_manual_data_table(force, absolute_position, loadcell_limit, force_offset)


    # if absolute_position is None:
    #     absolute_position = '-'
    #     test_progress = '-'
    # else:
    #     absolute_position = round(absolute_position, 2)

    #     if test_parameters is None:
    #         test_progress = None
    #     elif test_parameters['test_type'] == 'monotonic':
    #         initial_absolute_position = test_parameters['initial_gauge_length']['value'] - test_parameters['clamps_distance']['value']
    #         test_progress = ((absolute_position - initial_absolute_position) / test_parameters['displacement']['value']) * 100
    #         test_progress = round(test_progress, 1)
    #     elif test_parameters['test_type'] == 'cyclic':
    #         pass

    # table = Table(box=box.ROUNDED)
    # table.add_column('Force', justify='center', min_width=12)
    # table.add_column('Absolute position', justify='center', min_width=20)
    # table.add_column('Load Cell usage', justify='center', min_width=12, style=loadcell_usage_style)

    # if test_parameters is None:
    #     table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %')
    # elif test_parameters['test_type'] == 'monotonic':
    #     table.add_column('Test progress', justify='center', min_width=12)        
    #     table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %', f'{test_progress} %')
    # elif test_parameters['test_type'] == 'cyclic':
    #     table.add_row(f'{force} N', f'{absolute_position} mm', f'{loadcell_usage} %')

    return table