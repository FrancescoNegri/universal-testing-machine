from statistics import mean, median
import time

import RPi.GPIO as GPIO
from hx711 import HX711
import scipy
import scipy.signal
from threading import Thread
import numpy as np
import pandas as pd


class LoadCell():
    def __init__(self, dat_pin:int, clk_pin:int):

        GPIO.setmode(GPIO.BCM)
        self._hx711 = HX711(dout_pin=dat_pin, pd_sck_pin=clk_pin)
        
        # Calibration attributes
        self.is_calibrated = False
        self._slope = None
        self._y_intercept = None
        self._tare_weight = 0

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

    def calibrate(self, calibrating_mass:float = None):
        zero_calibration_raw = None
        mass_calibration_raw = None

        lines_count = 0

        try:
            res = None
            while res != 'y' or bool(zero_calibration_raw) is False:
                res = input('Zero-mass point calibration. Ready? [y]\n')
                lines_count += 2
                if res == 'y':
                    zero_calibration_raw = self._get_raw_data_mean(n_readings=100)             
                    if bool(zero_calibration_raw) is False:
                        print('Failed. Retry...')
                        lines_count += 1

            res = None
            while res != 'y' or bool(mass_calibration_raw) is False:
                res = input('Known-mass point calibration. Add the known mass. Ready? [y]\n')
                lines_count += 2
                if res == 'y':
                    mass_calibration_raw = self._get_raw_data_mean(n_readings=100)               
                    if bool(mass_calibration_raw) is False:
                        print('Failed. Retry...')
                        lines_count += 1
                    
            if calibrating_mass is None:
                calibrating_mass = input('Enter the known mass used for calibration (in grams): ')
                calibrating_mass = float(calibrating_mass)
                lines_count += 2
            
            x0 = zero_calibration_raw
            y0 = 0
            x1 = mass_calibration_raw
            y1 = calibrating_mass

            self._slope = (y1 - y0) / (x1 - x0)
            self._y_intercept = (y0*x1 - y1*x0) / (x1 - x0)

            self.is_calibrated = True
        except:
            pass
        
        return self.is_calibrated, lines_count

    def _get_raw_data_mean(self, n_readings:int = 1, kernel_size:int = 5):
        if n_readings == 1:
            mean_value = self._hx711.get_raw_data_mean(readings=1)
        else:
            readings = []
            for _ in range(n_readings):
                readings.append(self._hx711.get_raw_data_mean(readings=1))
        
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
        
        if self.is_calibrated:
            weights = self._slope * readings + self._y_intercept
            forces = (weights / 1000) * 9.81
            data = {'t': timings, 'F': forces}
            is_force = True
        else:
            data = {'t': timings, 'raw': readings}
            is_force = False

        # TODO: eventualmente aggiungere qui vari filtri e post elaborazione dei dati
        
        df = pd.DataFrame.from_dict(data, orient='index')
        df = df.transpose()

        return df, is_force

    def _read(self):
        while self._is_reading:
            try:
                self._readings.append(self._hx711._read())
                self._timings.append(time.time())
            except:
                pass

        return

    def is_batch_ready(self, batch_index:int, batch_size:int = 5):
        if len(self._readings) - batch_index >= batch_size:
            return True
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
                print('batch:')
                print(batch)
                print('batch[i]:')
                print(batch[i])
                print('batch median:')
                print(batch_median)
                batch[i] = batch_median
        
        batch = scipy.signal.medfilt(batch, kernel_size)

        if self.is_calibrated:
            batch = self._slope * batch + self._y_intercept
            batch = (batch / 1000) * 9.81
            batch = pd.DataFrame({'t': batch_timings, 'F': batch})
            is_force = True
        else:
            batch = pd.DataFrame({'t': batch_timings, 'raw': batch})
            is_force = False

        return batch, batch_index, is_force