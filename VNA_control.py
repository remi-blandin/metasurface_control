import pyvisa
import numpy as np
import matplotlib.pyplot as plt

__all__ = ["VNA"]

class VNA:
    
    """A class to communicate with a VNA easily"""
    
    def __init__(self, visa_adress = "TCPIP0::192.168.1.3::inst0::INSTR"):
        
        self.visa_adress = visa_adress
        self.rm = pyvisa.ResourceManager()

        self.initialize()
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def initialize(self, timeout = 20000):
        
        self.device = self.rm.open_resource(self.visa_adress)
        self.device.timeout = timeout
        
        print(self.device.query("*IDN?"))
        self.device.write("FORM REAL,64")      # 64-bit floating point
        self.device.write("FORM:BORD SWAP") 
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    
    def get_S_param(self, s_param='S11', channel=1, plot=False):

        # Get existing measurements
        cat = self.device.query(f"CALC{channel}:PAR:CAT?")
        cat = cat.replace('"', '').strip()
    
        meas_name = None
    
        if cat:
            entries = cat.split(',')
            for i in range(0, len(entries), 2):
                name = entries[i]
                param = entries[i+1]
                if param.upper() == s_param.upper():
                    meas_name = name
                    break
    
        # If not found, create it
        if meas_name is None:
            meas_name = f"AUTO_{s_param}"
            print(f"Creating measurement {meas_name} -> {s_param}")
            self.device.write(
                f"CALC{channel}:PAR:DEF '{meas_name}',{s_param}"
            )
    
        # Select the measurement
        self.device.write(
            f"CALC{channel}:PAR:SEL '{meas_name}'"
        )
    
        # Trigger sweep and wait until finished
        self.device.write(f"INIT{channel}:IMM")
        self.device.query("*OPC?")
    
        # Read S-parameter complex data
        data = self.device.query_binary_values(
            f"CALC{channel}:DATA? SDATA",
            datatype='d',
            container=np.array
        )
    
        s_complex = data[0::2] + 1j * data[1::2]
    
        # Read frequency axis
        freq = self.device.query_binary_values(
            f"CALC{channel}:X?",
            datatype='d',
            container=np.array
        ) / 1e9  # convert to GHz
        
        if plot:
            plt.plot(freq, 20*np.log10(np.abs(s_complex)))
            plt.xlabel("Frequency (GHz)")
            plt.ylabel("Magnitude (dB)")
            plt.show()
    
        return freq, s_complex
    
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #