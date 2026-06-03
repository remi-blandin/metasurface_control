import uhd
import numpy as np
import threading
import queue
import time

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
        
        # =========================
        # RING BUFFER ADDITIONS
        # =========================
        
        self.buffer_size = 2**18  # ~260k samples (adjust as needed)
        self.rx_buffer = np.zeros(self.buffer_size, dtype=np.complex64)
        self.write_idx = 0
        self.rx_running = False
        self.total_rx_samples = 0
        self.last_meas_nb_rx_samples = 0
        self.last_packet_time = 0.
        
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

    def get_time_now(self):
    
        return self.usrp.get_time_now().get_real_secs()

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
        
    def start_rx_old(self):

        self.rx_buffer = np.zeros(8192, dtype=np.complex64)
        self.rx_metadata = uhd.types.RXMetadata()

        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = True
        self.rx_streamer.issue_stream_cmd(stream_cmd)
        
        # Warm-up flush: discard a few recv() calls, NOT a sleep
        for _ in range(10):
            self.rx_streamer.recv(self.rx_buffer, self.rx_metadata, timeout=0.1)
            
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def start_rx(self, buffer_len=4096):
    
        self.rx_buffer_len = buffer_len
        self.rx_metadata = uhd.types.RXMetadata()

        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = True
        self.rx_streamer.issue_stream_cmd(stream_cmd)

        self.rx_running = True
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
    
    def _rx_loop(self):
        tmp = np.empty(self.rx_buffer_len, dtype=np.complex64)
        md = self.rx_metadata

        while self.rx_running:
            num_rx = self.rx_streamer.recv(tmp, md, timeout=0.1)
            self.total_rx_samples += num_rx

            if num_rx > 0:
            
                self.last_packet_time = md.time_spec.get_real_secs()
            
                wi = self.write_idx  # local copy (important)
                end = wi + num_rx
                
                if end < self.buffer_size:
                    self.rx_buffer[wi:end] = tmp[:num_rx]
                else:
                    first = self.buffer_size - wi
                    self.rx_buffer[wi:] = tmp[:first]
                    self.rx_buffer[:num_rx-first] = tmp[first:num_rx]

                # single integer update (no lock)
                self.write_idx = (wi + num_rx) % self.buffer_size
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def flush_rx(self):
        while True:
            num_rx = self.rx_streamer.recv(
                self.rx_buffer, self.rx_metadata, timeout=0.0
            )
            if num_rx == 0:
                break
                
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #
                
    def get_measurement_old(self, num_samples):
        samples = np.zeros(num_samples, dtype=np.complex64)
        # discard old buffered data
        
        start = time.perf_counter()
        
        self.flush_rx()
        
        t1 = time.perf_counter()
        
        received = 0
        num_rx = self.rx_streamer.recv(
            samples[received:], self.rx_metadata, timeout=1.0
        )
        print(f"Numrx {num_rx}")
        
        received = 0
        calls = 0
        while received < num_samples:
            num_rx = self.rx_streamer.recv(
                samples[received:], self.rx_metadata, timeout=1.0
            )
#            if num_rx > 0:
            calls += 1
            received += num_rx
        print(f"{calls=}, {received=}")
                
        t2 = time.perf_counter()
        
        print(f"Time flush: {t1 - start} s")
        print(f"Time receive: {t2 - t1}s")
        
        return samples
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def get_measurement(self, num_samples, from_time_now=True):
    
        if num_samples > self.buffer_size:
            raise ValueError("Request exceeds ring buffer size")
            
        if from_time_now:
            min_start_time = self.get_time_now()
        else:
            min_start_time = 0.
            
        while (self.last_packet_time < min_start_time) or \
            (self.total_rx_samples - self.last_meas_nb_rx_samples < num_samples):
#            print('loop')
#            print(f"Time diff = {self.last_packet_time < min_start_time}")
#            print(f"Nb smp diff = {self.total_rx_samples - self.last_meas_nb_rx_samples}")
            self.last_meas_nb_rx_samples = self.total_rx_samples
            time.sleep(0.0001)
            
#        print('Measurement extraction')
#        print(f"Time diff = {self.last_packet_time < min_start_time}")
#        print(f"Nb smp diff = {self.total_rx_samples - self.last_meas_nb_rx_samples}")
            
        self.last_meas_nb_rx_samples = self.total_rx_samples
    
        idx = self.write_idx

        if idx >= num_samples:
            return self.rx_buffer[idx-num_samples:idx].copy()

        else:
            return np.concatenate([
                self.rx_buffer[self.buffer_size-(num_samples-idx):],
                self.rx_buffer[:idx]
            ])
            
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def stop(self):
    
        self.tx_running = False
        self.rx_running = False

        self.tx_thread.join()
        if hasattr(self, "rx_thread"):
            self.rx_thread.join()

        # Stop RX stream
        stop_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        self.rx_streamer.issue_stream_cmd(stop_cmd)
        
        # Properly terminate TX stream
        metadata = uhd.types.TXMetadata()
        metadata.start_of_burst = False
        metadata.end_of_burst = True
        
        # Send empty packet to signal end
        self.tx_streamer.send(np.zeros(1, dtype=np.complex64), metadata)
