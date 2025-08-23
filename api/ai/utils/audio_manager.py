import wave
import io
import subprocess
import tempfile

class AudioManager:

    def __init__(self):
        """DOC
        Initializes the AudioManager instance.
        No arguments.
        """
        pass

    def preprocess_wav(self, wav_bytes):
        """DOC
        Applies basic preprocessing (noise reduction, bandpass filtering) to WAV audio bytes using ffmpeg.

        Args:
            wav_bytes (bytes): The input audio data in WAV format.

        Returns:
            bytes: The preprocessed audio data in WAV format.
        """
        with tempfile.NamedTemporaryFile(suffix=".wav") as in_file, \
            tempfile.NamedTemporaryFile(suffix=".wav") as out_file:
            in_file.write(wav_bytes)
            in_file.flush()
            cmd = [
                "ffmpeg", "-y", "-i", in_file.name,
                "-af", "afftdn,highpass=f=300,lowpass=f=3400",
                "-ar", "16000", "-ac", "1", "-f", "wav", out_file.name
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg preprocessing failed: {result.stderr.decode()}")
            out_file.seek(0)
            return out_file.read()
    
    def convert_webm_to_wav(self, webm_bytes):
        """DOC
        Converts WebM/Opus audio bytes to WAV format using ffmpeg.

        Args:
            webm_bytes (bytes): The input audio data in WebM/Opus format.

        Returns:
            bytes: The converted audio data in WAV format.
        """
        with tempfile.NamedTemporaryFile(suffix=".webm") as webm_file, \
             tempfile.NamedTemporaryFile(suffix=".wav") as wav_file:
            webm_file.write(webm_bytes)
            webm_file.flush()
            cmd = [
                "ffmpeg", "-y", "-i", webm_file.name,
                "-ar", "16000", "-ac", "1", "-f", "wav", wav_file.name
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")
            wav_file.seek(0)
            return wav_file.read()

    def create_wav_from_chunk(self, chunk_bytes, sample_width=2, channels=1, framerate=16000):
        """DOC
        Wraps raw PCM audio bytes in a WAV header, or re-creates a WAV file from existing WAV bytes.

        Args:
            chunk_bytes (bytes): The input audio data (raw PCM or WAV).
            sample_width (int): Sample width in bytes (default: 2).
            channels (int): Number of audio channels (default: 1).
            framerate (int): Sample rate in Hz (default: 16000).

        Returns:
            bytes: Audio data in valid WAV format.
        """
        try:
            buffer = io.BytesIO(chunk_bytes)
            with wave.open(buffer, 'rb') as wf:
                params = wf.getparams()
                new_buffer = io.BytesIO()
                with wave.open(new_buffer, 'wb') as new_wf:
                    new_wf.setparams(params)
                    new_wf.writeframes(wf.readframes(params.nframes))
                return new_buffer.getvalue()
        except wave.Error:
            new_buffer = io.BytesIO()
            with wave.open(new_buffer, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(sample_width)
                wf.setframerate(framerate)
                wf.writeframes(chunk_bytes)
            return new_buffer.getvalue()

    def skip_seconds_wav(self, wav_bytes, seconds_to_skip):
        """DOC
        Skips a specified number of seconds from the beginning of a WAV audio byte stream.

        Args:
            wav_bytes (bytes): The input audio data in WAV format.
            seconds_to_skip (float): Number of seconds to skip from the start.

        Returns:
            bytes: WAV audio data with the initial seconds skipped.
        """
        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, 'rb') as wf:
            framerate = wf.getframerate()
            sample_width = wf.getsampwidth()
            channels = wf.getnchannels()
            total_frames = wf.getnframes()
            frames_to_skip = int(framerate * seconds_to_skip)
            wf.setpos(frames_to_skip)
            remaining_frames = wf.readframes(total_frames - frames_to_skip)

        out_buffer = io.BytesIO()
        with wave.open(out_buffer, 'wb') as out_wf:
            out_wf.setnchannels(channels)
            out_wf.setsampwidth(sample_width)
            out_wf.setframerate(framerate)
            out_wf.writeframes(remaining_frames)
        return out_buffer.getvalue()
    
    def get_wav_duration(self, wav_bytes):
        """
        Get the duration of a WAV audio byte stream.

        Args:
            wav_bytes (bytes): The input audio data in WAV format.

        Returns:
            float: The duration of the audio in seconds.
        """
        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, 'rb') as wf:
            framerate = wf.getframerate()
            total_frames = wf.getnframes()
            duration = total_frames / framerate
        return duration