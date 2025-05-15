
import threading
import time
import sys

class Spinner:
    def __init__(self, message="Running"):
        self.message = message
        self.running = False
        self.thread = None
        self.start_time = None
        self.duration = 0

    def start(self):
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()

    def _spin(self):
        spinner_chars = "|/-\\"
        i = 0
        while self.running:
            elapsed = time.time() - self.start_time
            sys.stdout.write(f"\r⏳ {spinner_chars[i % 4]} {self.message}... [Elapsed: {elapsed:.1f}s]")
            sys.stdout.flush()
            self.duration = elapsed
            i += 1
            time.sleep(0.1)
        sys.stdout.write("\r Done.                                                                                               \n")

    def elapsedTime(self):
        return self.duration
    
    def stop(self):
        if self.running:
            self.running = False
            self.thread.join()
