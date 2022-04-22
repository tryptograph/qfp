from __future__ import division

from .audio import load_audio
from .utils import stft, find_peaks, generate_hash, n_strongest
from .quads import find_quads
import hashlib
import librosa
import numpy as np
import warnings as w

class fpType:
    """
    Parameters for reference/query fingerprint types
    Presented in order (q, r, c, w, h)

    Tuple is used to ensure immutability

    q = quads to create per root point (A)
    r = width of search window
    c = distance from root point to position window
    w = width of max filter
    h = height of max filter

    based on stft hop-size of 32 samples (4ms):
    ref.r =    800ms / 4ms =  200
    ref.c =   1375ms / 4ms = ~345
    que.r =   1300ms / 4ms =  325
    que.c = 1437.5ms / 4ms = ~360

    query filter height/width are calculated as:
    query.w = ref.w / (1 + .2) = 125
    query.h = ref.h * (1 - .2) = 60

    reference width changed from 151 to 150 so that
    result is an int for epsilon of .2 (20% change in speed/tempo)
    """
    #             Q    R    C    W    H
    Reference = (9, 200, 345, 150,  75)
    # Query =     (9, 200, 345, 150,  75)
    # Query =  (20, 325, 360, 125, 60)
    Query = (20, 325, 360, 150, 75)
    # Query = (500, 345, 360, 125, 60) #Original parameters

class Fingerprint:

    def __init__(self, path, fp_type):
        self.path = path
        if fp_type is not fpType.Reference and fp_type is not fpType.Query:
            raise TypeError(
                "Fingerprint must be of type 'Reference' or 'Query'")
        else:
            self.params = fp_type

    def create(self, snip=None):
        """
        Creates quad hashes for a given audio file
        """
        q, r, c, w, h = self.params
        samples = load_audio(self.path, snip=snip)
        spectrogram = stft(samples)
        self.peaks = list(find_peaks(spectrogram, w, h))
        quads = find_quads(self.peaks, r, c)
        self.strongest = n_strongest(spectrogram, quads, q)
        self.hashes = [generate_hash(q) for q in self.strongest]

    def create_file_hash(self, block_size: int = 4096):
        sha1 = hashlib.sha1()
        with open(self.path, "rb") as f:
            while True:
                buf = f.read(block_size)
                if not buf:
                    break
                sha1.update(buf)
        return sha1.hexdigest().upper()

    def bpm_detector(self):
        w.filterwarnings('ignore')
        y = librosa.load(self.path, sr=16000, mono=True)
        y = y[0]
        tempo, beat_frames = librosa.beat.beat_track(y)
        return round(tempo)
        # print("Tempo: {:.2f}".format(tempo))

class ReferenceFingerprint(Fingerprint):

    def __init__(self, path):
        self.fp_type = fpType.Reference
        Fingerprint.__init__(self, path, fp_type=self.fp_type)




class QueryFingerprint(Fingerprint):

    def __init__(self, path):
        self.matches = None
        self.fp_type = fpType.Query
        Fingerprint.__init__(self, path, fp_type=self.fp_type)

    def create(self):
        Fingerprint.create(self, snip=10)
