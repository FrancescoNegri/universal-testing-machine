import os
import time
import pyqtgraph as pg
from pyqtgraph.functions import mkPen
import pandas as pd
from rich.console import Console
from rich.live import Live
console = Console()
from utility import utility
import scipy.signal
from gpiozero import Button
from controller import controller
from loadcell import loadcell
from src import constants, helpers, table

# HACK: suppress Qt5 polluting error messages
from pyqtgraph.Qt import QtCore
def handler(msg_type, msg_log_context, msg_string):
    pass
QtCore.qInstallMessageHandler(handler)
# HACK: end suppression

def _init_plot_data(plot_item, plot_color):
    plot_data = plot_item.plot(
    pen=None, symbol=constants.PLOTS_SYMBOL, symbolSize=constants.PLOTS_SYMBOL_SIZE)
    plot_data.opts['useCache'] = True
    plot_data.setSymbolPen(mkPen(plot_color))

    forces = []
    strains = []

    return plot_data, forces, strains

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

        plot_data, forces, strains = _init_plot_data(plot_item, plot_color)
        batch_index = 0

        # FIXME: suppress libEGL warning message

        live_table = Live(
            table.generate_data_table(None, None, None, None),
            refresh_per_second=12,
            transient=True
        )

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
                        if (plot_data.getData()[1] is not None) and (len(plot_data.getData()[1]) > 500):
                            plot_data, forces, strains = _init_plot_data(plot_item, plot_color)

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
                        table.generate_data_table(
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

        plot_data, forces, strains = _init_plot_data(plot_item, plot_color)
        batch_index = 0

        fixed_strain = ((my_controller.get_absolute_position() - initial_absolute_position) / initial_gauge_length) * 100

        # FIXME: suppress libEGL warning message

        live_table = Live(
            table.generate_data_table(None, None, None, None),
            refresh_per_second=12,
            transient=True
        )

        my_loadcell.start_reading()
        t0 = my_controller.hold_torque()

        with live_table:
            while my_controller.is_holding:
                if stop_flag or time.time() - t0 >= delay:
                    my_controller.release_torque()
                else:
                    while my_loadcell.is_batch_ready(batch_index):
                        if (plot_data.getData()[1] is not None) and (len(plot_data.getData()[1]) > 500):
                            plot_data, forces, strains = _init_plot_data(plot_item, plot_color)
                        
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
                        table.generate_data_table(
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

def _start_monotonic_test(my_controller: controller.LinearController, my_loadcell: loadcell.LoadCell, test_parameters: dict, stop_button_pin: int):
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

    xlim = round((displacement / initial_gauge_length) * 1.1 * 100)  # 10% margin
    ylim = loadcell_limit
    plot_item.getViewBox().setRange(xRange=(0, xlim), yRange=(0, ylim))
    plot_item.setLabel('bottom', 'Strain', '%')
    plot_item.setLabel('left', 'Force', 'N')
    plot_item.setTitle('Force vs. Strain')

    data, stop_flag = _run_go(
        my_controller,
        my_loadcell,
        plot_item=plot_item,
        plot_color=constants.PLOT_COLORS_LIST[0],
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

def _start_cyclic_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, stop_button_pin: int):
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
    plot_color_idx = 0

    xlim = round((cyclic_upper_limit / initial_gauge_length) * 1.1 * 100)  # 10% margin
    ylim = loadcell_limit
    plot_item.getViewBox().setRange(xRange=(0, xlim), yRange=(0, ylim))
    plot_item.setLabel('bottom', 'Strain', '%')
    plot_item.setLabel('left', 'Force', 'N')
    plot_item.setTitle('Force vs. Strain')

    data_list = []
    data_labels_list = []

    # PRETENSIONING PHASE
    if is_pretensioning_set:
        # PRETENSIONING PHASE - GO
        plot_color_idx += 1
        reference_absolute_position = initial_absolute_position
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
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
        plot_color_idx += 1
        data, stop_flag = _run_delay(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
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
        plot_color_idx += 1
        reference_absolute_position = my_controller.get_absolute_position()
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
            speed=pretensioning_return_speed,
            displacement=reference_absolute_position -
            (initial_absolute_position + cyclic_lower_limit),
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
        plot_color_idx += 1
        data, stop_flag = _run_delay(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
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
        plot_color_idx += 1
        reference_absolute_position = my_controller.get_absolute_position()
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
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
        plot_color_idx += 1
        data, stop_flag = _run_delay(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
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
        plot_color_idx += 1
        reference_absolute_position = my_controller.get_absolute_position()
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
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
        plot_color_idx += 1
        if cycle_idx < (int(cycles_number) - 1):
            data, stop_flag = _run_delay(
                my_controller,
                my_loadcell,
                plot_item=plot_item,
                plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
                delay=cyclic_delay,
                stop_flag=stop_flag,
                stop_button=stop_button,
                initial_absolute_position=initial_absolute_position,
                test_parameters=test_parameters
            )
            if data is not None:
                data_list.append(data)
                data_labels_list.append('cycle_' + str(cycle_idx) + '_delay')
            plot_color_idx -= 4

    # FAILURE PHASE
    if is_failure_set:
        plot_item.getViewBox().enableAutoRange(axis='x')

        # FAILURE PHASE - BEFORE DELAY
        plot_color_idx += 1
        data, stop_flag = _run_delay(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
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
        plot_color_idx += 1
        reference_absolute_position = my_controller.get_absolute_position()
        data, stop_flag = _run_go(
            my_controller,
            my_loadcell,
            plot_item=plot_item,
            plot_color=constants.PLOT_COLORS_LIST[plot_color_idx],
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

def _start_static_test(my_controller: controller.LinearController, my_loadcell: loadcell.LoadCell, stop_button_pin: int):
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

    xlim = 30  # in seconds
    ylim = loadcell_limit
    plot_item.getViewBox().setRange(xRange=(0, xlim), yRange=(0, ylim))
    plot_item.setLabel('bottom', 'Time', 's')
    plot_item.setLabel('left', 'Force', 'N')
    plot_item.setTitle('Force vs. Time')

    plot_data = plot_item.plot(pen=None, symbol=constants.PLOTS_SYMBOL, symbolSize=constants.PLOTS_SYMBOL_SIZE)
    plot_data.opts['useCache'] = True
    plot_data.setSymbolPen(mkPen(constants.PLOT_COLORS_LIST[0]))

    timings = []
    forces = []
    batch_index = 0

    live_table = Live(
        table.generate_data_table(None, None, None, None),
        refresh_per_second=12,
        transient=True
    )

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
                    table.generate_data_table(
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

def start_test(my_controller:controller.LinearController, my_loadcell:loadcell.LoadCell, test_parameters:dict, test_dir:str, stop_button_pin:int):
    data = None
    data_labels = None

    if test_parameters['test_type'] == constants.MONOTONIC:
        data = _start_monotonic_test(
            my_controller=my_controller,
            my_loadcell=my_loadcell,
            test_parameters=test_parameters,
            stop_button_pin=stop_button_pin
        )
    elif test_parameters['test_type'] == constants.CYCLIC:
        data, data_labels = _start_cyclic_test(
            my_controller=my_controller,
            my_loadcell=my_loadcell,
            test_parameters=test_parameters,
            stop_button_pin=stop_button_pin
        )
    elif test_parameters['test_type'] == constants.STATIC:
        data = _start_static_test(
            my_controller=my_controller,
            my_loadcell=my_loadcell,
            stop_button_pin=stop_button_pin
        )

    with console.status('Postprocessing test data...'):
        if data is not None:
            data = helpers.postprocess_data(data, test_parameters)

    console.print('[#e5c07b]>[/#e5c07b]', 'Postprocessing test data...', '[green]:heavy_check_mark:[/green]')

    with console.status('Saving test data...'):
        # Save .xlsx file
        extension = '.xlsx'
        filename = test_parameters['test_id'] + extension
        if data is not None:
            writer = pd.ExcelWriter(os.path.join(test_dir, filename))

            if isinstance(data, list):
                data_list = data
                for idx, _ in enumerate(data_list):
                    data_list[idx].to_excel(writer, sheet_name=data_labels[idx], index=False)
            else:
                data.to_excel(writer, sheet_name=test_parameters['test_id'], index=False)

            writer.save()

        # Save complete .csv file
        extension = '.csv'
        filename = test_parameters['test_id'] + extension
        if data is not None:
            if isinstance(data, list):
                data = pd.concat(data, ignore_index=True)

            data.to_csv(os.path.join(test_dir, filename), index=False)

    console.print('[#e5c07b]>[/#e5c07b]', 'Saving test data...', '[green]:heavy_check_mark:[/green]')

    return