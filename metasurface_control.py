import serial
import time
import numpy as np
import random
import matplotlib.pyplot as plt

__all__ = ["metasurface"]

class metasurface:
    
    """A class to communicate with a metasurface easily"""
    
    def __init__(self, PORT = "COM3", BAUD = 1000000):
        
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
                        
        self.idx_shift_next = np.array([
                        [6, 7, 4, 5, 2, 3, 0, 1],
                        [15, 16, 17, 14, 10, 11, 8, 9],
                        [20, 23, 22, 21, 18, 19, 13, 12],
                        [30, 31, 28, 29, 26, 27, 24, 25],
                        [39, 40, 41, 38, 34, 35, 32, 33],
                        [44, 47, 46, 45, 42, 43, 37, 36],
                        [54, 55, 52, 53, 50, 51, 48, 49],
                        [63, 64, 65, 62, 58, 59, 56, 57],
                        [68, 71, 70, 69, 66, 67, 61, 60],
                        [78, 79, 76, 77, 74, 75, 72, 73],
                        [87, 88, 89, 86, 82, 83, 80, 81],
                        [92, 95, 94, 93, 90, 91, 85, 84]
        ])
        
        self.idx_shift_next_new = self.idx_shift_next[:,1:].flatten()
        self.idx_shift_next_prev = self.idx_shift_next[:,:-1].flatten()
        
        self.idx_order_shift = np.fliplr(self.idx_shift_next).flatten()
        self.idx_new = self.idx_shift_next[:, 0]
        
        self.ser = serial.Serial(PORT, BAUD)
        time.sleep(2)  
        
        self.nb_cells = 96
        self.set_config([False] * self.nb_cells)
        self.ser.reset_input_buffer()
        
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
        plt.show(block=False)
        
        return fig, ax
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def send_configuration(self, config=None, print_messages = False):
        
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
        
        ack = self.ser.read(1)

        if ack != b'\x06':
            raise RuntimeError("Invalid ACK")
    
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def send_uniform_config(self, state=False):
        
        config = [state] * self.nb_cells
        return(self.send_configuration(config))
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def send_random_config(self, print_messages=False):
        
        config = [random.choice([True, False]) for _ in range(self.nb_cells)]
        return(self.send_configuration(config, print_messages=print_messages))
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def save_config(self, file_name):
    
        np.save(file_name, np.array(self.config))
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def set_config_from_file(self, file_name, print_messages=False):
    
        cfg = np.load(file_name)
        config = list(cfg)
        return(self.send_configuration(config, print_messages=print_messages))
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def intermediate_configs(self, config):
    
        # calculate in which order the elements are sent to the shift registers
        order_shift_reg = np.reshape(config[self.idx_order_shift], (12, 8))
        
        configs_interm = np.array([[False]*9]*96)
        configs_interm[:,0] = self.config
        
        for n in range(8):
            # shift the indexes
            configs_interm[self.idx_shift_next_new, n+1] = \
                configs_interm[self.idx_shift_next_prev, n]
                
            configs_interm[self.idx_new, n+1] = order_shift_reg[:,n]
            
        return configs_interm
        
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
            plt.show(block=False)
