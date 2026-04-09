import serial
import time
import numpy as np
import matplotlib.pyplot as plt

__all__ = ["metasurface"]

class metasurface:
    
    """A class to communicate with a metasurface easily"""
    
    def __init__(self, PORT = "COM3", BAUD = 115200):
        
        self.PORT = PORT
        self.BAUD = BAUD
        
        # this is the mapping between the indexes of pins of the connector and 
        # the cells of the metasurface
        self.idx_map = [1 , 0, 3, 2, 5, 4, 7, 6, 9, 8,11,10,
                        16,17,12,15,14,13,19,18,23,20,21,22,
                        25,24,27,26,29,28,31,30,33,32,35,34,
                        40,41,36,39,38,37,43,42,47,44,45,46,
                        49,48,51,50,53,52,55,54,57,56,59,58,
                        64,65,60,63,62,61,67,66,71,68,69,70,
                        73,72,75,74,77,76,79,78,81,80,83,82,
                        88,89,84,87,86,85,91,90,95,92,93,94]
        
        self.ser = serial.Serial(PORT, BAUD)
        time.sleep(2)  
        
        self.set_config([False]*96)
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def set_config(self, config):
        
        if len(config) != 96:
            raise ValueError("Need 96 states")
            
        # reorder the elements of the configuration according to the cell 
        # to pin map
        self.config = config

        config_pin_ordered = [False]*96
        cnt = 0
        for i in self.idx_map:
            config_pin_ordered[i] = self.config[cnt]
            cnt = cnt + 1
        
        self.config_pin_ordered = config_pin_ordered
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def plot_config(self):
        
        conf = np.array(self.config).reshape((8, 12))
        
        plt.imshow(conf)
        plt.show()
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def send_configuration(self, config=None, time_sleep=0.1, print_messages = False):
        
        if config is not None:
            self.set_config(config)
            
        bytes_to_send = []
        
        for reg in range(12):

            byte = 0
            for bit in range(8):

                if self.config_pin_ordered[reg*8 + bit]:
                    byte |= (1 << (7-bit))

            bytes_to_send.append(byte)

        self.ser.write(bytearray(bytes_to_send))
        
        if print_messages:
            print("Bytes sent: " + str(bytes_to_send))
        line = self.ser.read_until()
        if print_messages:
            print(line.decode().strip())
        
        time.sleep(time_sleep)
        line = self.ser.read_until()
        if print_messages:
            print(line.decode().strip())
