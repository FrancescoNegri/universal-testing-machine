from rich import box
from rich.table import Table

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