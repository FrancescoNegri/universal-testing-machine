# Universal Testing Machine

A Raspberry Pi based Universal Testing Machine to perform a number of tasks related to mechanical tensile tests of specimens. 

## Table of Contents

- [Universal Testing Machine](#universal-testing-machine)
  - [Table of Contents](#table-of-contents)
  - [Requirements](#requirements)
  - [Installation & Usage](#installation--usage)
  - [Software Features](#software-features)
    - [Monotonic Test](#monotonic-test)
    - [Cyclic Test](#cyclic-test)
    - [Static Test](#static-test)
  - [Hardware List](#hardware-list)

## Requirements
This project has been developed for `Python 3.9` on Raspberry Pi 3 and 4, running Raspberry Pi OS 11 (`Bullseye` distribution).

The following packages are to be installed through Raspberry Pi `apt` package manager:
- `SciPy 1.6.0-2 (python3-scipy)`
- `pandas 1.1.5+dfsg-2 (python3-pandas)`
- `PyQt5 5.12.2+dfsg-3 (python3-pyqt5)`

The following packages are to be installed through `pip`:
- `InquirerPy 0.2.4`
- `rich 10.13.0`
- `pyqtgraph 0.12.3`

## Installation & Usage

It is assumed to start from a fresh installation of Raspberry Pi OS (`Bullseye` distribution) with _ssh_ enabled, such that it can be configured headless.

In case you plan to use your Raspberry Pi directly by connecting it to a screen, start directly from step 6.

Then, follow the steps below in order to obtain a working version of this software on your Raspberry Pi:

1. Insert the newly formatted microSD card into the proper Raspberry Pi slot.
2. Plug the Raspberry Pi into its power supply and wait a few seconds for it to turn on.
3. Open a terminal window and connect your computer to the Raspberry Pi through _ssh_ protocol. In case a warning saying _"REMOTE HOST IDENTIFICATION HAS CHANGED!"_ is thrown, go to your known hosts file and delete its content.
4. Once succesfully connected to the Raspberry Pi via _ssh_, type the `sudo raspi-config` command and enable the _VNC_ interface.
5. At this point, close the _ssh_ connection and connect through the _VNC_ graphic interface.
6. Open a terminal window on the Raspberry Pi and update the installed packages via `sudo apt update`, followed by `sudo apt upgrade`.
7. Reboot the Raspberry Pi by typing `sudo reboot`.
8. As soon as the Raspberry Pi is once again ready, open a new terminal and move to the Desktop via the command `cd Desktop`.
9. Clone this repository to your Raspberry Pi by using the `git clone` command.
10. Move into the new repository folder thanks to `cd universal-testing-machine`.
11. Install `SciPy` library  by launching `sudo apt install python3-scipy`.
12. Install `pandas` library by typing `sudo apt install python3-pandas`.
13. Install `PyQt5` by using `sudo apt install python3-pyqt5`.
14. Install all of the remaining libraries through the command `sudo pip install -r requirements.txt`.

Once completed all the previously described steps, your Raspberry Pi should be ready to execute this software. To do so, launch the command below:
```sh
python universal-testing-machine/
```

## Software Features

This software allows for three different types of test.

### Monotonic Test

It refers to a classical monotonic tensile test. A specimen is loaded into the UTM clamps and then it is tested by running the machine at a given speed for a desired distance. It measures force and displacement, which can easily be converted to stress and strain. The test ends either when the crossbar reaches the specified distance or when the test is manually interrupted by the operator.

### Cyclic Test

Under development.

### Static Test

Under development.

## Hardware List

The software running this project is fully parametric, therefore the connections between the required devices and the Raspberry Pi are not reported here. However, a full list summarizing all the necessary components to run the universal testing machine through the code provided in this repo is available below:

Soon available.
