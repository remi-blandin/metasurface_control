"""
libreVNA.py - Client TCP pour communiquer avec LibreVNA-GUI via SCPI.

Basé sur la bibliothèque officielle du projet LibreVNA (https://github.com/jankae/LibreVNA).
Communique avec le serveur SCPI intégré à LibreVNA-GUI (port TCP 19542 par défaut).
"""

import socket
import json
import threading
import time
import numpy as np
import matplotlib.pyplot as plt


class SocketStreamReader:
    """Lecteur de flux socket avec gestion de buffer."""

    def __init__(self, sock: socket.socket, default_timeout=1):
        self._sock = sock
        self._buffer = b""
        self._default_timeout = default_timeout

    def readline(self, timeout=None):
        t = timeout if timeout is not None else self._default_timeout
        self._sock.settimeout(t)
        return self.readuntil(b"\n")

    def readuntil(self, separator: bytes = b"\n") -> bytes:
        while separator not in self._buffer:
            data = self._sock.recv(4096)
            if not data:
                raise ConnectionError("Connexion fermée par le serveur")
            self._buffer += data
        idx = self._buffer.index(separator) + len(separator)
        result = self._buffer[:idx]
        self._buffer = self._buffer[idx:]
        return result


class libreVNA:
    """Client SCPI pour LibreVNA-GUI."""

    def __init__(self, host: str = "localhost", port: int = 19542,
                 check_cmds: bool = True, timeout: float = 1):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((host, port))
        except Exception:
            raise ConnectionError(
                f"Impossible de se connecter à LibreVNA-GUI sur {host}:{port}. "
                "Vérifiez que LibreVNA-GUI est lancé."
            )
        self.reader = SocketStreamReader(self.sock, default_timeout=timeout)
        self.default_check_cmds = check_cmds
        self._lock = threading.Lock()

    def __del__(self):
        try:
            self.sock.close()
        except Exception:
            pass

    def get_status(self, timeout=None):
        """Lit le registre d'état (Event Status Register)."""
        self.sock.sendall(b"*ESR?\n")
        response = self.reader.readline(timeout=timeout).decode().rstrip()
        return int(response)

    def cmd(self, command: str, check=None, timeout=None):
        """Envoie une commande SCPI (sans réponse attendue).

        Si check est True (ou si default_check_cmds est True),
        vérifie le registre d'état après la commande.
        """
        with self._lock:
            self.sock.sendall(command.encode())
            self.sock.send(b"\n")
            if check or (check is None and self.default_check_cmds):
                status = self.get_status(timeout=timeout)
                if status & 0x20:
                    raise RuntimeError(f"Command Error après '{command}'")
                if status & 0x10:
                    raise RuntimeError(f"Execution Error après '{command}'")
                if status & 0x08:
                    raise RuntimeError(f"Device Error après '{command}'")
                if status & 0x04:
                    raise RuntimeError(f"Query Error après '{command}'")
                return status
            return None

    def query(self, query_str: str, timeout=None) -> str:
        """Envoie une requête SCPI et retourne la réponse."""
        with self._lock:
            self.sock.sendall(query_str.encode())
            self.sock.send(b"\n")
            return self.reader.readline(timeout=timeout).decode().rstrip()

    @staticmethod
    def parse_VNA_trace_data(data: str):
        """
        Parse les données de trace VNA.

        Retourne une liste de tuples (frequency_Hz, complex_value).
        Le format brut est : [(freq, real, imag), (freq, real, imag), ...]
        """
        result = []
        try:
            # Remplacer les parenthèses par des crochets si nécessaire
            cleaned = data.replace("(", "[").replace(")", "]")
            # Ajouter les crochets englobants si absents
            if not cleaned.startswith("["):
                cleaned = "[" + cleaned + "]"
            elif not cleaned.startswith("[["):
                cleaned = "[" + cleaned + "]"
            parsed = json.loads(cleaned)
            for point in parsed:
                freq = point[0]
                real = point[1]
                imag = point[2]
                result.append((freq, complex(real, imag)))
        except (json.JSONDecodeError, IndexError) as e:
            raise ValueError(f"Impossible de parser les données de trace : {e}")
        return result

    @staticmethod
    def parse_SA_trace_data(data: str):
        """
        Parse les données de trace analyseur de spectre.

        Retourne une liste de tuples (frequency_Hz, amplitude_dB).
        """
        result = []
        try:
            parsed = json.loads(data.replace("(", "[").replace(")", "]"))
            for point in parsed:
                freq = point[0]
                amplitude = point[1]
                result.append((freq, amplitude))
        except (json.JSONDecodeError, IndexError) as e:
            raise ValueError(f"Impossible de parser les données SA : {e}")
        return result
    
    def load_calibration(self, calibration_file):
        
        """Charge un fichier de calibration (.cal) dans le VNA.

        Le fichier .cal doit se trouver dans le même dossier que LibreVNA-GUI.exe.
        La commande SCPI est une query : :VNA:CAL:LOAD? <filename>
        """
        print(f"\nChargement de la calibration : {calibration_file}")
        result = self.query(f":VNA:CAL:LOAD? {calibration_file}", timeout=5)
        if result.strip().upper() != "TRUE":
            raise RuntimeError(
                f"Échec du chargement de la calibration '{calibration_file}'. "
                f"Vérifiez que le fichier est dans le dossier de LibreVNA-GUI.exe. "
                f"Réponse : {result}"
            )
        print("Calibration chargée.")

    def get_S_param(self, s_param='S11', timeout=60, plot=False):
        
        """Attend la fin de l'acquisition (sweep + moyennage)."""
        start = time.time()
        while True:
            finished = self.query(":VNA:ACQ:FIN?")
            if finished.strip().lower() in ("true", "1"):
                break
            if time.time() - start > timeout:
                raise TimeoutError(f"Acquisition non terminée après {timeout}s")
            time.sleep(0.1)
            
        raw_data = self.query(f":VNA:TRACE:DATA? {s_param}")
        data = np.array(self.parse_VNA_trace_data(raw_data))
        freq = np.abs(data[:,0])
        s_complex = data[:,1]
        
        if plot:
            plt.plot(freq, 20*np.log10(np.abs(s_complex)))
            plt.show()
        
        return freq, s_complex
            
            