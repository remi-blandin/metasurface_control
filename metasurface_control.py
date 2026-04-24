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
        
        self.nb_cells = 96
        self.set_config([False] * self.nb_cells)
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def set_config(self, config):
        
        if len(config) != self.nb_cells:
            raise ValueError("Need 96 states")
            
        # reorder the elements of the configuration according to the cell 
        # to pin map
        self.config = config

        config_pin_ordered = [False] * self.nb_cells
        cnt = 0
        for i in self.idx_map:
            config_pin_ordered[i] = self.config[cnt]
            cnt = cnt + 1
        
        self.config_pin_ordered = config_pin_ordered
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def plot_config(self, fig=None, ax=None):
        
        conf = np.array(self.config).reshape((8, 12))
        
        if (fig == None) or (ax == None):        
            fig = plt.figure()    
            ax = fig.add_subplot(111)
        
        ax.imshow(conf)
        plt.show()
        
        return fig, ax
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def send_configuration(self, config=None, time_sleep=0.1, 
                           print_messages = False):
        
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
            
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def send_uniform_config(self):
        
        config = [False] * self.nb_cells
        self.send_configuration(config)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def optimize(self, cost_function, device, nb_repeat=1, print_cost=True,
        plot_progression=True):
        
        # optimize the metasurface configuration to maximize the cost returned
        # by the cost function given as argument
        
        config = [False] * self.nb_cells
        self.send_configuration(config)
            
        cost = np.zeros(self.nb_cells * nb_repeat + 1)
        cost[0] = cost_function(device)
        if print_cost:
            print("It 0, cost: " + str(cost[0]))
        max_cost = cost[0]

        for r in range(0, nb_repeat):
            for idx in range(0,self.nb_cells):
                
                idx_it = r * self.nb_cells + idx + 1
                
                config[idx] = not(config[idx])
                self.send_configuration(config)
                
                cost[idx_it] = cost_function(device)
                if print_cost:
                    print("It " + str(idx_it) + \
                          ", cost: " + \
                              str(cost[idx_it]))
                
                if cost[idx_it] < max_cost:
                    config[idx] = not(config[idx])
                    self.send_configuration(config)
                else:
                    max_cost = cost[idx_it]

        if plot_progression:
            plt.figure()
            plt.plot(cost)
            plt.xlabel('Iteration number')
            plt.ylabel('Cost function')
            plt.savefig('cost_function.png')
            plt.show()