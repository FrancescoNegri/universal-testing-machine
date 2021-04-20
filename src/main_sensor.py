import time
from load_cell import LoadCell
import RPi.GPIO as GPIO
import matplotlib.pyplot as plt
import numpy as np

lc = LoadCell(dat_pin=5, clk_pin=6)

lc.calibrate(298.27)


fig = plt.figure()
ax2=plt.axes()
line, = ax2.plot([], lw=3)
text = ax2.text(0.8,0.5, "")
ax2.set_xlim(0, 18+2)
ax2.set_ylim([0, 350])
fig.canvas.draw()   # note that the first draw comes before setting data

ax2background = fig.canvas.copy_from_bbox(ax2.bbox)

plt.show(block=False)

load = []
timing = []
line.set_data(timing,load)

lc.start_reading()

i = 0
while i < 100:
    if lc.is_ready():
        i += 1
        print('\n')
        print(i)
        batch, batch_index = lc.get_measurement()
        time_labels = np.arange(batch_index, batch_index+5, 1)*1/80
        load.extend(batch)
        timing.extend(time_labels)
        
        line.set_data(timing, load)
        
        print(batch)
        print(time_labels)

        # restore background
        fig.canvas.restore_region(ax2background)

        # redraw just the points
        ax2.draw_artist(line)
        ax2.draw_artist(text)

        # fill in the axes rectangle
        fig.canvas.blit(ax2.bbox)

        # in this post http://bastibe.de/2013-05-30-speeding-up-matplotlib.html
        # it is mentionned that blit causes strong memory leakage.
        # however, I did not observe that.
        fig.canvas.flush_events()

n_readings = lc.stop_reading()
print(f'plotted data: {len(load)}')
print(f'sensor data: {n_readings}')


GPIO.cleanup()