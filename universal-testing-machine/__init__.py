from InquirerPy import inquirer, validator
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
    pin_end_up=25,
    pin_end_down=8
)

my_loadcell = loadcell.LoadCell(
    dat_pin=5,
    clk_pin=6
)

result = 0

while result is not None:
    result = inquirer.select(
        message='Select a menu voice:',
        choices=[
                {'name': 'Mass Calibration', 'value': 1},
                {'name': 'Manual Control', 'value': 2},
                {'name': 'Monotonic Test', 'value': 3},
                {'name': 'Cyclic Test', 'value': 4},
                {'name': 'Exit', 'value': None}
        ],
        default=3
    ).execute()

    if result == 2:
        print('Not implemented yet.')
    elif result == 3:
        # adjustment_position = float(inquirer.text(
        #     message='Specify the crossbar initial position [mm]:',
        #     default='50',
        #     validate=validator.NumberValidator()
        # ).execute())
        # helpers.calibrate_controller(my_controller=my_controller, adjustment_position=adjustment_position)

        calibration_dir = helpers.create_calibration_dir()
        helpers.check_existing_calibration(calibration_dir, my_loadcell)
        if my_loadcell.is_calibrated is not True:
            helpers.calibrate_loadcell(my_loadcell, calibration_dir)

    elif result == 4:
        print('Not implemented yet.')
