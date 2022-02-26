import sys

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