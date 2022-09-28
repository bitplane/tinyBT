import collections
import logging
import select
import socket
import threading

from .threadmanager import ThreadManager


class NetworkSocket(object):
    def __init__(self, name):
        self._log = logging.getLogger(self.__class__.__name__).getChild(name)
        self._threads = ThreadManager(self._log)
        self._lock = threading.Lock()

        self._send_event = threading.Event()
        self._send_queue = collections.deque()
        self._send_try = 0

        self._recv_event = threading.Event()
        self._recv_queue = collections.deque()

        self._force_show_info = False
        self._threads.start_continuous_thread(self._info_thread, thread_interval=0.5)
        self._threads.start_continuous_thread(self._send_thread)
        self._threads.start_continuous_thread(self._recv_thread)

    # Non-blocking send
    def sendto(self, *args):
        self._send_queue.append(args)
        with self._lock:  # set send flag
            self._send_event.set()

    # Blocking read - with timeout
    def recvfrom(self, timeout=None):
        result = None
        if self._recv_event.wait(timeout):
            if self._recv_queue:
                result = self._recv_queue.pop()
            with self._lock:
                if not self._recv_queue and not self._threads.shutdown_in_progress():
                    self._recv_event.clear()
        return result

    def close(self):
        with self._lock:
            self._threads.shutdown()
            self._send_queue.clear()
            self._recv_queue.clear()
            self._send_event.set()
            self._recv_event.set()
        self._close()
        self._threads.join()

    # Private members #################################################

    def _info_thread(self):
        if (
            (len(self._recv_queue) > 20)
            or (len(self._send_queue) > 20)
            or self._force_show_info
        ):
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug(
                    "recv: %4d, send: %4d"
                    % (len(self._recv_queue), len(self._send_queue))
                )
            self._force_show_info = True
        if not (len(self._recv_queue) or len(self._send_queue)):
            self._force_show_info = False

    def _send_thread(self, send_tries=100):
        if self._send_event.wait(0.1):
            if self._send_queue:
                if self._send(*self._send_queue[0]):
                    self._send_queue.popleft()
                    self._send_try = 0
                elif self._send_try > send_tries:
                    self._send_queue.popleft()
                else:
                    self._send_queue.rotate(-1)
                    self._send_try += 1

            with self._lock:  # clear send flag
                if not self._send_queue and not self._threads.shutdown_in_progress():
                    self._send_event.clear()

    def _send(self, *args):
        raise NotImplementedError()

    def _recv_thread(self):
        tmp = self._recv()
        if tmp:
            self._recv_queue.append(tmp)
            with self._lock:
                self._recv_event.set()

    def _recv(self):
        raise NotImplementedError()

    def _close(self):
        raise NotImplementedError()


class UDPSocket(NetworkSocket):
    def __init__(self, connection):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(0)
        self._sock.bind(connection)
        NetworkSocket.__init__(self, "%s:%d" % connection)

    def _send(self, *args):
        select.select([], [self._sock], [], 0.1)
        try:
            self._sock.sendto(*args)
            return True
        except socket.error:
            pass

    def _recv(self):
        select.select([self._sock], [], [], 0.1)
        try:
            return self._sock.recvfrom(64 * 1024)
        except socket.error:
            pass

    def _close(self):
        self._sock.close()
