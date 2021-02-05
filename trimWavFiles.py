# Run from CMD or Powershell like so:
# python D:\path\to\trimWavFiles.py "D:\path\to\target_directory"
# or just copy this script file into the target directory, right click and select
# Open with > Python 
# or 
# Open with > Choose another app > Python
# This script can be run with Python version 2 or 3.
import os
import sys
import wave
from threading import Thread
if sys.version[0] == "2":
    from Queue import Queue
else:
    from queue import Queue

# Number of threads to use for multithreading. As a rule of thumb, use up to the
# number of (logical) CPU cores you have.
threads = 4
# Number of seconds to remove from the beginning of each audio file.
seconds_to_remove = 1
# Set this to "True" if you only want to keep the trimmed version of each file.
# (Use caution, as it may not be possible to recover deleted files.)
delete_originals = True

# Finds wav files in the directory tree rooted at [topdir] and returns them as a list.
def getWavs(topdir):
    wavs = []
    for root, dirs, files in os.walk(topdir):
        for file in files:
            if file[-4:] == ".wav":
                wavs.append(os.path.join(root, file))
    return sorted(wavs)

# Creates a new wav file containing the same data as the old one but omitting
# the first [rem_seconds] of audio.
def trimWav(wav_path, rem_seconds, del_orig = False):
    in_wav = wave.open(wav_path, 'r') # Open the original file in read mode
    in_params = in_wav.getparams() # tuple: (nchannels, sampwidth, framerate, nframes, comptype, compname)
    framerate, in_frames = in_params[2], in_params[3]
    # Set up the output file. Params should be the same except for nframes.
    out_path = wav_path[:-4] + "_trimmed.wav"
    out_wav = wave.open(out_path, 'w')
    out_frames = in_frames - (framerate * rem_seconds)
    out_wav.setparams(in_params)
    out_wav.setnframes(out_frames)
    # Skip the first n seconds of in_wav, then write the rest of the data to out_wav
    in_wav.setpos(framerate * rem_seconds) 
    out_wav.writeframes(in_wav.readframes(out_frames))
    in_wav.close()
    # Calculate the duration of the original and trimmed files
    in_dur, out_dur = float(in_frames) / framerate, float(out_frames) / framerate
    str_durs = "%.3f,%.3f" % (in_dur, out_dur)
    if del_orig:
        os.remove(wav_path)
    # Return info for the log file
    return [wav_path, out_path, str_durs]

# Worker threads that will do the actual trimming.
class TrimWorker(Thread):
    def __init__(self, inqueue, outqueue):
        Thread.__init__(self)
        self.inqueue = inqueue
        self.outqueue = outqueue

    def run(self):
        while True:
            trimCmd = self.inqueue.get()
            output = trimWav(*trimCmd)
            self.inqueue.task_done()
            self.outqueue.put(output)

def main():
    # Target directory can be passed to the script as a command-line argument; if not,
    # the directory containing the script will be used.
    try:
        target_dir = sys.argv[1]
    except:
        target_dir = sys.path[0]

    wavs = getWavs(target_dir)

    if len(wavs) > 0:
        print("Trimming %d .wav files..." % len(wavs))
        inqueue, outqueue = Queue(), Queue()
        
        for wav in wavs:
            inqueue.put((wav, seconds_to_remove, delete_originals))
        
        # Initialize n worker threads and "join" inqueue (i.e., suspend execution
        # of the main thread until the queue is empty)
        for i in range(threads):
            worker = TrimWorker(inqueue, outqueue)
            worker.daemon = True
            worker.start()
        inqueue.join()
        
        # Retrieve data from outqueue to write to the log file.
        log_data = []
        while not outqueue.empty():
            log_data.append(outqueue.get())
        # Write the log file.
        log_path = os.path.join(target_dir, "Wav_file_trim_log.csv")
        with open(log_path, 'w') as logfile:
            logfile.write("Original,Trimmed,Duration_orig,Duration_trimmed\n")
            logfile.write('\n'.join([','.join(x) for x in sorted(log_data)]))
        
        # Console will stay open after script has finished. 
        try:
            exit_prompt = input("Log file written to %s.\nPress Enter to close." % log_path)
        except:
            exit()
    
    else:
        try:
            exit_prompt = input("No .wav files found. Press Enter to close.")
        except:
            exit()

if __name__ == "__main__":
    main()