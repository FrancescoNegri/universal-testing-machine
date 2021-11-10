from datetime import datetime
from statistics import mean, median
import time
import RPi.GPIO as GPIO
from loadcell.hx711 import HX711
import scipy
import scipy.signal
from scipy import constants as scipy_constants
from threading import Thread
import numpy as np
import pandas as pd
import json

#HACK#
import random
def read_placeholder():
    time.sleep(0.0125)
    return random.randint(100000, 111111)

class LoadCell():
    def __init__(self, dat_pin:int, clk_pin:int):

        GPIO.setmode(GPIO.BCM)
        self._hx711 = HX711(dout_pin=dat_pin, pd_sck_pin=clk_pin)
        
        # Calibration attributes
        self.is_calibrated = False
        self._limit = None
        self._slope = None
        self._y_intercept = None
        self._calibrating_mass = None
        self._calibration_filename = 'load_cell_calibration.json'

        # Reading attributes
        self._is_reading = False
        self._readings = None
        self._timings = None
        self._started_reading_at = None
        self._read_thread = None

    def _reset_reading_attributes(self):
        self._is_reading = False
        self._readings = None
        self._timings = None
        self._started_reading_at = None
        self._read_thread = None

        return
    
    def _init_reading_attributes(self):
        self._readings = []
        self._timings = []
        self._is_reading = True

        self._read_thread = Thread(target=self._read)
        self._started_reading_at = time.time()

        return

    def _save_calibration(self, calibration_dir:str):
        with open(calibration_dir + r'/' + self._calibration_filename, 'w') as f:
            json.dump(self.get_calibration(), f)
        
        return

    def get_calibration(self):
        if self.is_calibrated:
            calibration = {
                'loadcell_limit': {
                    'value': self._limit,
                    'unit': 'N'
                },
                'slope': self._slope,
                'y_intercept': self._y_intercept,
                'calibrating_mass': {
                    'value': self._calibrating_mass,
                    'unit': 'g'
                },
                'date': datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
            }
        else:
            calibration = None
        
        return calibration

    def set_calibration(self, calibration:dict):
        self._limit = calibration['loadcell_limit']['value']
        self._slope = calibration['slope']
        self._y_intercept = calibration['y_intercept']
        self._calibrating_mass = calibration['calibrating_mass']['value']
        self.is_calibrated = True
        
        return

    def calibrate(self, loadcell_limit:int, zero_raw:int, mass_raw:int, calibrating_mass:float, calibration_dir:str):
        x0 = zero_raw
        y0 = 0
        x1 = mass_raw
        y1 = calibrating_mass

        self._limit = loadcell_limit
        self._slope = (y1 - y0) / (x1 - x0)
        self._y_intercept = (y0*x1 - y1*x0) / (x1 - x0)
        self._calibrating_mass = calibrating_mass
        self.is_calibrated = True

        self._save_calibration(calibration_dir=calibration_dir)
        return

    def _get_raw_data_mean(self, n_readings:int = 1, kernel_size:int = 5, fake:bool = False):
        if n_readings == 1:
            if fake is False: 
                mean_value = self._hx711.get_raw_data_mean(readings=1)
            else:
                mean_value = read_placeholder()
        else:
            readings = []

            if fake is False:
                for _ in range(n_readings):
                    readings.append(self._hx711.get_raw_data_mean(readings=1))
            else:
                for _ in range(n_readings):
                    readings.append(read_placeholder())
        
            readings = scipy.signal.medfilt(readings, kernel_size=kernel_size)
            mean_value = mean(readings)
        
        return mean_value

    def start_reading(self):
        self._init_reading_attributes()
        self._read_thread.start()

        return

    def stop_reading(self):
        readings = np.array(self._readings)
        timings = np.array(self._timings)
        
        self._reset_reading_attributes()
        
        weights = self._slope * readings + self._y_intercept
        forces = (weights / 1000) * scipy_constants.g
        data = {'t': timings, 'readings': readings, 'F': forces}

        # TODO: eventualmente aggiungere qui vari filtri e post elaborazione dei dati
        
        df = pd.DataFrame.from_dict(data, orient='index')
        df = df.transpose()

        return df

    def _read(self):
        while self._is_reading:
            try:
                #HACK#
                self._readings.append(self._hx711._read())
                # self._readings.append(read_placeholder())
                self._timings.append(time.time())
            except:
                pass

        return

    def is_batch_ready(self, batch_index:int, batch_size:int = 15):
        if self._readings is not None:
            if len(self._readings) - batch_index >= batch_size:
                return True
            else:
                return False
        else:
            return False

    def get_batch(self, batch_index:int, batch_size:int = 15, kernel_size:int = 5):
        batch = np.array(self._readings[batch_index:batch_index + batch_size])
        batch_timings = np.array(self._timings[batch_index:batch_index + batch_size])
        batch_index += batch_size
        
        batch_median = median(batch)
        reading_tolerance = 0.5 # 50%

        for i in range(len(batch)):
            reading = batch[i]
            if abs(reading) > abs(batch_median) * (1 + reading_tolerance) or abs(reading) < abs(batch_median) * (1 - reading_tolerance):
                batch[i] = batch_median
        
        batch = scipy.signal.medfilt(batch, kernel_size)

        batch = self._slope * batch + self._y_intercept
        batch = (batch / 1000) * scipy_constants.g
        batch = pd.DataFrame({'t': batch_timings, 'F': batch})

        return batch, batch_index