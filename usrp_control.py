import uhd
import numpy as np
import threading
import queue

__all__ = ["usrp"]

class usrp:

    """A class to communicate with an USRP"""
    
    def __init__(self, center_freq=5.2e9, gain_RX=20, gain_TX=20):
    
        self.usrp = uhd.usrp.MultiUSRP()
        print(self.usrp.get_mboard_name())
        
        self.sample_rate = 10e6
        self.gain_RX = gain_RX
        self.gain_TX = gain_TX
        self.center_freq = center_freq
        
        self.setup_usrp()
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def setup_usrp(self):
        # Basic configuration
        self.usrp.set_tx_rate(self.sample_rate)
        self.usrp.set_rx_rate(self.sample_rate)

        self.usrp.set_tx_freq(self.center_freq)
        self.usrp.set_rx_freq(self.center_freq)

        self.usrp.set_tx_gain(self.gain_TX)
        self.usrp.set_rx_gain(self.gain_RX)
        
        self.usrp.set_rx_dc_offset(False)

        self.usrp.set_tx_antenna("TX/RX")
        self.usrp.set_rx_antenna("RX2")  

        # Create streamers ONCE
        self.tx_streamer = self.usrp.get_tx_stream(
            uhd.usrp.StreamArgs("fc32", "sc16")
        )

        self.rx_streamer = self.usrp.get_rx_stream(
            uhd.usrp.StreamArgs("fc32", "sc16")
        )
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def set_time_now(self):
    
        self.usrp.set_time_now(uhd.types.TimeSpec(0.0))
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def send_const_sig(self, nb_sp_2_send = None, ampl=0.5):
        
        if nb_sp_2_send is None:
            nb_sp_2_send = int(0.01 * self.sample_rate)
        else:
            nb_sp_2_send = int(nb_sp_2_send)
            
        # Configure TX
        self.usrp.set_tx_rate(self.sample_rate)
        self.usrp.set_tx_freq(self.center_freq)
        self.usrp.set_tx_gain(self.gain_TX)
        self.usrp.set_tx_antenna("TX/RX")
        
        # generate IQ signal
        samples_to_send = ampl * \
            np.ones(nb_sp_2_send).astype(np.complex64)
            
        # Send signal
        tx_streamer = self.usrp.get_tx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))
        metadata = uhd.types.TXMetadata()
        metadata.start_of_burst = True
        metadata.end_of_burst = True
        tx_streamer.send(samples_to_send, metadata)

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #        
        
    def send_const_sig_timed(self, duration=0.05, ampl=0.5, tx_time=0.1):
        num_samps = int(duration * self.sample_rate)

        # Configure TX
        self.usrp.set_tx_rate(self.sample_rate)
        self.usrp.set_tx_freq(self.center_freq)
        self.usrp.set_tx_gain(self.gain_TX)
        self.usrp.set_tx_antenna("TX/RX")

        # Create constant signal
        samples = (ampl * np.ones(num_samps)).astype(np.complex64)

        tx_streamer = self.usrp.get_tx_stream(
            uhd.usrp.StreamArgs("fc32", "sc16")
        )

        metadata = uhd.types.TXMetadata()
        metadata.start_of_burst = True
        metadata.end_of_burst = True

        # schedule transmission
        metadata.has_time_spec = True
        metadata.time_spec = uhd.types.TimeSpec(tx_time)

        tx_streamer.send(samples, metadata)
            
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def read_sig(self, nb_sp_2_read = None, offset_off = True):
    
        if nb_sp_2_read is None:
            nb_sp_2_read = int(0.001 * self.sample_rate)
        else:
            nb_sp_2_read = int(nb_sp_2_read)
            
        if offset_off:
            self.usrp.set_rx_dc_offset(False)
            
        return self.usrp.recv_num_samps(nb_sp_2_read, self.center_freq, 
            self.sample_rate, [0], self.gain_RX) 
            
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
            
    def read_sig_timed(self, duration=0.05, rx_time=0.09, timeout=0.5):
        num_samps = int(duration * self.sample_rate)

        # Configure RX
        self.usrp.set_rx_rate(self.sample_rate)
        self.usrp.set_rx_freq(self.center_freq)
        self.usrp.set_rx_gain(self.gain_RX)
        self.usrp.set_rx_antenna("RX2")
        self.usrp.set_rx_dc_offset(False)

        rx_streamer = self.usrp.get_rx_stream(
            uhd.usrp.StreamArgs("fc32", "sc16")
        )

        buffer = np.zeros(num_samps, dtype=np.complex64)

        metadata = uhd.types.RXMetadata()

        # 🔑 Start streaming BEFORE TX
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = False
        stream_cmd.time_spec = uhd.types.TimeSpec(rx_time)
        rx_streamer.issue_stream_cmd(stream_cmd)
        
        
        samps_recvd = 0
        max_attempts = 50   # prevents infinite loop
        attempts = 0

        while samps_recvd < num_samps and attempts < max_attempts:
            num_rx = rx_streamer.recv(
                buffer[samps_recvd:], metadata, timeout=timeout
            )

            if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                print("RX error:", metadata.strerror())
                break

            if num_rx > 0:
                samps_recvd += num_rx
            else:
                attempts += 1  # nothing received → avoid infinite loop
                
            print(str(num_rx) + " " + str(samps_recvd) + " " + str(attempts))

        # Stop streaming
        stop_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        rx_streamer.issue_stream_cmd(stop_cmd)

        return buffer
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
        
    def start_tx(self, ampl=0.5, buffer_len=4096):
    
        self.tx_running = True

        # Constant signal buffer
        self.tx_buffer = (ampl * np.ones(buffer_len)).astype(np.complex64)

        metadata = uhd.types.TXMetadata()
        metadata.start_of_burst = False
        metadata.end_of_burst = False

        def tx_worker():
            while self.tx_running:
                self.tx_streamer.send(self.tx_buffer, metadata)

        self.tx_thread = threading.Thread(target=tx_worker)
        self.tx_thread.start()
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

#    def start_rx(self):
#    
#        self.rx_running = True

#        self.rx_buffer_len = 4096
#        self.rx_buffer = np.zeros(self.rx_buffer_len, dtype=np.complex64)

#        self.rx_queue = queue.LifoQueue()

#        metadata = uhd.types.RXMetadata()

#        # Start streaming immediately
#        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
#        stream_cmd.stream_now = True
#        self.rx_streamer.issue_stream_cmd(stream_cmd)

#        def rx_worker():
#            while self.rx_running:
#                num_rx = self.rx_streamer.recv(
#                    self.rx_buffer, metadata, timeout=1.0
#                )

#                if num_rx > 0:
#                    self.rx_queue.put(self.rx_buffer[:num_rx].copy())

#        self.rx_thread = threading.Thread(target=rx_worker)
#        self.rx_thread.start()
        
    def start_rx(self):
        self.rx_streamer = self.usrp.get_rx_stream(
            uhd.usrp.StreamArgs("fc32", "sc16")
        )

        self.rx_buffer = np.zeros(8192, dtype=np.complex64)
        self.rx_metadata = uhd.types.RXMetadata()

        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = True
        self.rx_streamer.issue_stream_cmd(stream_cmd)
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def flush_rx(self):
        while True:
            num_rx = self.rx_streamer.recv(
                self.rx_buffer, self.rx_metadata, timeout=0.0
            )
            if num_rx == 0:
                break

#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
        
#    def get_measurement(self, num_samples):
#        samples = []

#        while len(samples) < num_samples:
#            chunk = self.rx_queue.get()
#            samples.extend(chunk)

#        samples = np.array(samples[:num_samples])

#        return samples
        
    def get_measurement(self, num_samples):
        samples = np.zeros(num_samples, dtype=np.complex64)

        # 🔑 discard old buffered data
        self.flush_rx()

        received = 0
        while received < num_samples:
            num_rx = self.rx_streamer.recv(
                samples[received:], self.rx_metadata, timeout=1.0
            )

            if num_rx > 0:
                received += num_rx

#        # Optional: remove edges
#        samples = samples[1000:-1000]

#        # Optional: phase normalization
#        phase = np.angle(np.mean(samples))
#        samples *= np.exp(-1j * phase)

        return samples
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def stop(self):
    
        self.tx_running = False
        self.rx_running = False

        self.tx_thread.join()

        # Stop RX stream
        stop_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        self.rx_streamer.issue_stream_cmd(stop_cmd)
        
        # Properly terminate TX stream
        metadata = uhd.types.TXMetadata()
        metadata.start_of_burst = False
        metadata.end_of_burst = True
        
        # Send empty packet to signal end
        self.tx_streamer.send(np.zeros(1, dtype=np.complex64), metadata)
