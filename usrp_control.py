import uhd
import numpy as np
import threading
import queue
import time
from scipy.signal import find_peaks

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

    def extract_steps(self, signal, window=10, var_threshold_factor=10.0, margin=30,
        nb_steps = 8):
    
        """
        Automatically locate the region of a signal that contains steps,
        using a rolling variance detector.

        The baseline noise variance is estimated from the flattest parts of the
        signal. Samples whose local variance exceeds (baseline * var_threshold_factor)
        are considered 'active'. The contiguous active region is returned with an
        optional margin on each side.

        Parameters
        ----------
        signal               : 1D array-like
        window               : rolling variance window size (samples)
        var_threshold_factor : how many times above baseline variance to trigger
        margin               : extra samples to include on each side of the region

        Returns
        -------
        start, end  : indices (inclusive) of the extracted region
        roll_var    : the rolling variance array (for diagnostics)
        breakpoints : indices corresponding to the changes of changes of step
        steps       : start, end, mean and standard deviation of the steps
        mean_line   : reconstructed signal
        """
        n = len(signal)
        sig_real = np.real(signal)
        sig_imag = np.imag(signal)

        # Rolling variance via convolution (fast, no Python loop)
        half = window // 2
        roll_mean_real = np.convolve(sig_real, np.ones(window) / window, mode="same")
        roll_var_real  = np.convolve((sig_real - roll_mean_real) ** 2, 
            np.ones(window) / window, mode="same")
        roll_mean_imag = np.convolve(sig_imag, np.ones(window) / window, mode="same")
        roll_var_imag  = np.convolve((sig_imag - roll_mean_imag) ** 2, 
            np.ones(window) / window, mode="same")
        roll_var = roll_var_real + roll_var_imag
        
        # exclude start and end 
        roll_var[0:window] = 0
        roll_var[-window:] = 0

        # Estimate baseline variance from the bottom 20% of roll_var values
        # (avoids being biased by the active region)
        baseline_var = np.percentile(roll_var, 20)

        threshold = baseline_var * var_threshold_factor
        
        # -- Identify the steps ---------------------------------------------
        
        breakpoints, properties = find_peaks(
            roll_var,
            height=threshold,      # only peaks above threshold
            distance=25,           # minimum spacing between peaks (samples)
            prominence=threshold,  # ensures peaks are genuinely local maxima
        )
        
        if breakpoints.size < nb_steps:
            raise ValueError(
                f"No active region found. "
                f"Baseline var={baseline_var:.4f}, threshold={threshold:.4f}. "
                f"Try lowering var_threshold_factor."
            )
        
        # remove false detection and add missing changes
#        breakpoints = self.robust_periodic_event_detection(breakpoints, n, N_EVENTS=nb_steps)
        
        # add another breakpoint after the last one to take into account 
        # the final state
        breakpoints = np.append(breakpoints, breakpoints[-1] + margin)
        
        # -- Detect the active region --------------------------------------
        start = max(0,     breakpoints[0] - margin)
        end   = min(n - 1, breakpoints[-1] + margin)
        
        active = signal[start:end + 1]
        signal = signal[start:end + 1]
        n_act = len(signal)
        breakpoints = breakpoints - start - 1
        
        edges = [0] + breakpoints
        steps = []
        for a, b in zip(edges[:-1], edges[1:]):
            seg = signal[a:b]
            steps.append({"start": a, "end": b, "mean": np.median(seg), 
            "std": np.real(seg).std() + 1j * np.imag(seg).std(), "n": len(seg)})

        mean_line = np.zeros(n_act, dtype = np.complex64)
        for s in steps:
            mean_line[s["start"]:s["end"]] = s["mean"]

        return start, end, roll_var, breakpoints, steps, mean_line
        
#- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - #

    def robust_periodic_event_detection(self, detections, nb_samples, period=30, 
        N_EVENTS=8):
    
        MISS_PENALTY = 20
        FALSE_POS_PENALTY = 5
        MAX_MATCH_DIST = 5

        best_cost = np.inf
        best_grid = None
        best_assignment = None

        for T in range(period-3, period+3):

            for det in detections:

                for t0 in range(det - 5, det + 6):

                    grid = t0 + np.arange(N_EVENTS) * T

                    used = np.zeros(len(detections), dtype=bool)
                    assignment = []

                    cost = 0

                    for g in grid:

                        distances = np.abs(detections - g)
                        idx = np.argmin(distances)

                        if distances[idx] <= MAX_MATCH_DIST:
                            cost += distances[idx]
                            used[idx] = True
                            assignment.append(("detected", detections[idx]))
                        else:
                            cost += MISS_PENALTY
                            assignment.append(("missing", int(round(g))))

                    cost += FALSE_POS_PENALTY * np.sum(~used)

                    if cost < best_cost:
                        best_cost = cost
                        best_grid = grid
                        best_assignment = assignment

        # Build corrected sequence
        corrected_events = []

        for status, value in best_assignment:

            corrected_events.append(int(value))

        corrected_events = np.array(corrected_events)
        
        # check if the steps are cut
        if corrected_events[-1] >= nb_samples:
            raise ValueError("Error: step signal incomplete")

        print("Corrected sequence:")
        print(corrected_events)

        print("\nOrigin:")
        missing_event = False
        for i, (status, value) in enumerate(best_assignment):
            print(i, status, value)
            if status == "missing":
                missing_event = True
                
        if missing_event:
            raise ValueError("Strict detection: missing step")
        
        return corrected_events
            
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
