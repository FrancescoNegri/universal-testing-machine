from statistics import mean, median
import time
import RPi.GPIO as GPIO
from hx711 import HX711
import scipy
import scipy.signal
from threading import Thread

class LoadCell():
    def __init__(self, dat_pin : int, clk_pin : int):

        GPIO.setmode(GPIO.BCM)
        self._hx711 = HX711(dout_pin=dat_pin, pd_sck_pin=clk_pin)
        self.is_calibrated = False
        self._slope = None
        self._y_intercept = None
        self._tare_weight = 0

        # Reading attributes
        self._readings = None
        self._start_reading_at = None
        self._is_reading = False
        self._read_thread = None
        self._batch_index = 0
    
    def calibrate(self, calibrating_mass : float = None):
        zero_calibration_raw = None
        mass_calibration_raw = None

        lines_count = 0

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
        
        return self.is_calibrated, lines_count

    def _reset_reading_attributes(self):
        self._is_reading = False
        time.sleep(0.01)

        self._readings = None
        self._start_reading_at = None
        self._read_thread = None
        self._batch_index = 0

    def _get_raw_data_mean(self, n_readings : int = 1, kernel_size : int = 5):
        if n_readings == 1:
            mean_value = self._hx711.get_raw_data_mean(readings=1)
        else:
            readings = []
            for _ in range(n_readings):
                readings.append(self._hx711.get_raw_data_mean(readings=1))
        
            readings = scipy.signal.medfilt(readings, kernel_size=kernel_size)
            mean_value = mean(readings)
        
        return mean_value

    def start_reading(self, frequency : int = 80):
        self._readings = []
        self._is_reading = True

        self._read_thread = Thread(target=self._read, args=[frequency])
        self._read_thread.start()
        self._start_reading_at = time.time()

        return

    def stop_reading(self):        
        n_readings = len(self._readings)
        reading_time_interval = time.time() - self._start_reading_at
        self._reset_reading_attributes()

        return n_readings, reading_time_interval

    def _read(self, frequency : int = 80):
        cycle_start_time = time.time()
        cycle_period = 1 / frequency
        cycle_delay = 0

        while self._is_reading is True:
            current_time = time.time()
            elapsed_time = current_time - cycle_start_time

            if elapsed_time >= cycle_period - cycle_delay and self._is_reading is True:
                reading = False
                while reading is False:
                    reading = self._hx711._read()
                self._readings.append(reading)
                cycle_start_time = time.time()
                cycle_delay = cycle_start_time - current_time

    def is_ready(self, batch_size : int = 5):
        if len(self._readings) - self._batch_index >= batch_size:
            return True
        else:
            return False

    def get_measurement(self, batch_size : int = 5, kernel_size : int = 5):
        batch = self._readings[self._batch_index:self._batch_index + batch_size]
        self._batch_index += batch_size
        
        batch_median = median(batch)
        reading_tolerance = 0.2 # 20%
        for i in range(len(batch)):
            reading = batch[i]
            if reading > batch_median * (1 + reading_tolerance) or reading < batch_median * (1 - reading_tolerance):
                batch[i] = batch_median
        
        batch = scipy.signal.medfilt(batch, kernel_size)

        for i in range(len(batch)):
            batch[i] = self._slope * batch[i] + self._y_intercept

        return batch, self._batch_index - batch_size