# Universal Testing Machine

A Raspberry Pi based Universal Testing Machine to perform a number of tasks related to mechanical tensile tests of specimens. 

## Table of Contents

- [Universal Testing Machine](#universal-testing-machine)
  - [Table of Contents](#table-of-contents)
  - [Installation & Usage](#installation--usage)
  - [Software](#software)
    - [Monotonic Test](#monotonic-test)
    - [Cyclic Test](#cyclic-test)
    - [Static Test](#static-test)
  - [Hardware](#hardware)

Requirements

The following packages are required:

- Python 3.7
  
- SciPy 1.7.1
  
- Pandas 1.3.3
  
- Matplotlib 3.4.3
  
- InquirerPy 0.2.4
  
- Rich 10.11.0
  

## Installation & Usage

Clone this project **on your Raspberry Pi** and move into the main directory:

```sh
git clone https://github.com/FrancescoNegri/universal-testing-machine.git
cd universal-testing-machine
```

## Software

This software allows for three different types of test.

### Monotonic Test

It refers to a classical monotonic tensile test. A specimen is loaded into the UTM clamps and then it is tested by running the machine at a given speed for a desired distance. It measures force and displacement, which can easily be converted to stress and strain. The test ends either when the crossbar reaches the specified distance or when the test is manually interrupted by the operator.

### Cyclic Test

Not implemented yet.

### Static Test

Under development.

## Hardware

Available soon.