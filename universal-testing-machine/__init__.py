from InquirerPy import inquirer, validator
from rich.console import Console
console = Console()
import controller
import loadcell
import helpers

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
    clk_pin=6
)

console.rule('[bold red]UNIVERSAL TESTING MACHINE')

result = 0

while result is not None:
    result = inquirer.select(
        message='Select a menu voice:',
        choices=[
                {'name': 'Load Cell Calibration', 'value': 1},
                {'name': 'Manual Control', 'value': 2},
                {'name': 'Monotonic Test', 'value': 3},
                {'name': 'Cyclic Test', 'value': 4},
                {'name': 'Exit', 'value': None}
        ],
        default=3
    ).execute()

    if result == 1:
        calibration_dir = helpers.create_calibration_dir()
        helpers.check_existing_calibration(calibration_dir, my_loadcell)
        if my_loadcell.is_calibrated is not True:
            helpers.calibrate_loadcell(my_loadcell, calibration_dir)
    elif result == 2:
        helpers.start_manual_mode(
            my_controller,
            my_loadcell,
            speed=3,
            mode_button_pin=22,
            up_button_pin=17,
            down_button_pin=27
        )
    elif result == 3:
        adjustment_position = float(inquirer.text(
            message='Specify the crossbar initial position [mm]:',
            default='50',
            validate=validator.NumberValidator(float_allowed=True)
        ).execute())
        helpers.calibrate_controller(my_controller=my_controller)
        
        if my_controller.is_calibrated:
            helpers.adjust_crossbar_position(my_controller=my_controller, adjustment_position=adjustment_position)

            calibration_dir = helpers.create_calibration_dir()
            helpers.check_existing_calibration(calibration_dir, my_loadcell)
            if my_loadcell.is_calibrated is not True:
                helpers.calibrate_loadcell(my_loadcell, calibration_dir)

            helpers.start_manual_mode(
                my_controller,
                my_loadcell,
                speed=3,
                mode_button_pin=22,
                up_button_pin=17,
                down_button_pin=27
            )

            test_parameters = helpers.read_test_parameters(test_type='monotonic', default_clamps_distance=9.15)
            output_dir = helpers.create_output_dir(test_parameters)
            helpers.save_test_parameters(my_controller, my_loadcell, test_parameters, output_dir)

            helpers.start_test(
                my_controller,
                my_loadcell,
                test_parameters,
                output_dir=output_dir,
                stop_button_pin=22
            )
    elif result == 4:
        print('Not implemented yet.')
    
    console.rule()
