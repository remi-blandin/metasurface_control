import pyvisa
import numpy as np
import matplotlib.pyplot as plt

__all__ = ["VNA"]

class VNA:
    
    """A class to communicate with a VNA easily"""
    
    def __init__(self, visa_adress = "TCPIP0::192.168.1.3::inst0::INSTR"):
        
        self.visa_adress = visa_adress
        self.rm = pyvisa.ResourceManager()
        self._meas_cache = {}

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
        key = (channel, s_param.upper())
        meas_name = getattr(self, '_meas_cache', {}).get(key)

        if meas_name is None:
            if not hasattr(self, '_meas_cache'):
                self._meas_cache = {}
            cat = self.device.query(f"CALC{channel}:PAR:CAT?").replace('"', '').strip()
            entries = cat.split(',') if cat else []
            for i in range(0, len(entries), 2):
                if entries[i+1].upper() == s_param.upper():
                    meas_name = entries[i]
                    break

            if meas_name is None:
                meas_name = f"AUTO_{s_param}"
                print(f"Creating measurement {meas_name} -> {s_param}")
                self.device.write(f"CALC{channel}:PAR:DEF '{meas_name}',{s_param}")

            self._meas_cache[key] = meas_name

        self.device.write(f"CALC{channel}:PAR:SEL '{meas_name}'")

        # Trigger a single fresh sweep (blocks the channel from continuous mode)
        # and wait until it (and any averaging) is fully complete
        self.device.write(f"SENS{channel}:SWE:MODE SINGLE")
        self.device.query("*OPC?")

        data = self.device.query_binary_values(
            f"CALC{channel}:DATA? SDATA", datatype='d', container=np.array
        )
        s_complex = data[0::2] + 1j * data[1::2]

        freq = self.device.query_binary_values(
            f"CALC{channel}:X?", datatype='d', container=np.array
        ) / 1e9

        if plot:
            plt.plot(freq, 20*np.log10(np.abs(s_complex)))
            plt.xlabel("Frequency (GHz)")
            plt.ylabel("Magnitude (dB)")
            plt.show()

        return freq, s_complex
    
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def get_multiple_S_params(self, s_params=('S11', 'S21', 'S12', 'S22'), channel=1, plot=False):
        meas_names = {}

        # Ensure all requested measurements exist (create if missing)
        cat = self.device.query(f"CALC{channel}:PAR:CAT?").replace('"', '').strip()
        entries = cat.split(',') if cat else []
        existing = {entries[i + 1].upper(): entries[i] for i in range(0, len(entries), 2)}

        for s_param in s_params:
            key = (channel, s_param.upper())
            meas_name = self._meas_cache.get(key)

            if meas_name is None:
                meas_name = existing.get(s_param.upper())

                if meas_name is None:
                    meas_name = f"AUTO_{s_param}"
                    print(f"Creating measurement {meas_name} -> {s_param}")
                    self.device.write(f"CALC{channel}:PAR:DEF '{meas_name}',{s_param}")

                self._meas_cache[key] = meas_name

            meas_names[s_param.upper()] = meas_name

        # Trigger ONE single sweep for the whole channel
        self.device.write(f"SENS{channel}:SWE:MODE SINGLE")
        self.device.query("*OPC?")

        # Frequency axis is shared across all measurements on the channel
        freq = self.device.query_binary_values(
            f"CALC{channel}:X?", datatype='d', container=np.array
        ) / 1e9

        results = {}
        for s_param in s_params:
            meas_name = meas_names[s_param.upper()]
            self.device.write(f"CALC{channel}:PAR:SEL '{meas_name}'")

            data = self.device.query_binary_values(
                f"CALC{channel}:DATA? SDATA", datatype='d', container=np.array
            )
            s_complex = data[0::2] + 1j * data[1::2]
            results[s_param.upper()] = s_complex

        if plot:
            plt.figure()
            for s_param, s_complex in results.items():
                plt.plot(freq, 20 * np.log10(np.abs(s_complex)), label=s_param)
            plt.xlabel("Frequency (GHz)")
            plt.ylabel("Magnitude (dB)")
            plt.legend()
            plt.show()

        return freq, results