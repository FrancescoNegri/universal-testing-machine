import sys
import os
from datetime import datetime

def delete_last_lines(n_lines:int=1):
    for _ in range(n_lines):
        #cursor up one line
        sys.stdout.write('\x1b[1A')

        #delete last line
        sys.stdout.write('\x1b[2K')

def start_section(name):
    print(f'\n\t\t{name}')
    print('--------------------------------------------------')
    return

def end_section():
    print('--------------------------------------------------')
    return

def init_dirs():
    dir = os.path.dirname(__file__)
    path = '../.calibration'
    calibration_dir = os.path.join(dir, path)
    os.makedirs(calibration_dir, exist_ok=True)

    dir = os.path.dirname(__file__)
    path = '../output'
    dir_name = os.path.join(dir, path)
    os.makedirs(dir_name, exist_ok=True)

    date = datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
    output_dir = os.path.join(dir, path, date)
    os.makedirs(output_dir) 

    return output_dir, calibration_dir