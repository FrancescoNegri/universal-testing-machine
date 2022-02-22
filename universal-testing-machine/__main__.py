from InquirerPy import inquirer, validator
from rich.console import Console
console = Console()
from controller import controller
from loadcell import loadcell
import helpers
from src import calibration, configuration, test
from src import constants

my_controller = controller.LinearController(
    motor=controller.stepper.StepperMotor(
        total_steps=200,
        dir_pin=20, step_pin=13,
        en_pin=23,
        mode_pins=(14, 15, 18),
        mode=controller.stepper.ONE_THIRTYTWO,
        gear_ratio=5.18
    ),
    screw_pitch=5,
    up_endstop_pin=25,
    down_endstop_pin=8
)

my_loadcell = loadcell.LoadCell(
    dat_pin=5,
    clk_pin=6,
    clamp_grams=constants.CLAMP_GRAMS
)

console.rule('[bold red]UNIVERSAL TESTING MACHINE')

result = 0

while result is not None:
    result = inquirer.select(
        message='Select a menu voice:',
        choices=[
                {'name': 'Load Cell Calibration', 'value': 'loadcell_calibration'},
                {'name': 'Manual Control', 'value': 'manual'},
                {'name': 'Monotonic Test', 'value': 'monotonic'},
                {'name': 'Cyclic Test', 'value': 'cyclic'},
                {'name': 'Static Test', 'value': 'static'},
                {'name': 'Exit', 'value': None}
        ],
        default='monotonic'
    ).execute()

    if result == 'loadcell_calibration':
        calibration.calibrate_loadcell(my_loadcell)
    elif result == 'manual':
        helpers.start_manual_mode(
            my_controller,
            my_loadcell,
            speed=3,
            mode_button_pin=22,
            up_button_pin=17,
            down_button_pin=27
        )
    elif result == 'monotonic' or result == 'cyclic':
        adjustment_position = float(inquirer.text(
            message='Specify the crossbar initial position [mm]:',
            default='50',
            validate=validator.NumberValidator(float_allowed=True)
        ).execute())
        calibration.calibrate_controller(my_controller=my_controller)
        
        if my_controller.is_calibrated:
            helpers.adjust_crossbar_position(my_controller=my_controller, adjustment_position=adjustment_position)

            calibration.calibrate_loadcell(my_loadcell)

            helpers.start_manual_mode(
                my_controller,
                my_loadcell,
                speed=3,
                mode_button_pin=22,
                up_button_pin=17,
                down_button_pin=27
            )

            test_parameters = configuration.set_test_parameters(test_type=result)
            test_dir = helpers.create_test_dir(test_parameters, helpers.create_dir('./output'))
            helpers.save_test_parameters(my_controller, my_loadcell, test_parameters, test_dir)

            test.start_test(
                my_controller,
                my_loadcell,
                test_parameters,
                test_dir=test_dir,
                stop_button_pin=22
            )
    elif result == 'static':
        calibration.calibrate_loadcell(my_loadcell)
        
        helpers.start_manual_mode(
                my_controller,
                my_loadcell,
                speed=1,
                mode_button_pin=22,
                up_button_pin=17,
                down_button_pin=27
            )

        test_parameters = helpers.read_test_parameters(test_type=result)
        test_dir = helpers.create_test_dir(test_parameters, helpers.create_dir('./output'))
        helpers.save_test_parameters(my_controller, my_loadcell, test_parameters, test_dir)

        test.start_test(
                my_controller,
                my_loadcell,
                test_parameters,
                test_dir=test_dir,
                stop_button_pin=22
            )
    
    console.rule()
