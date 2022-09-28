import threading
import time


def start_thread(fun, *args, **kwargs):
    thread = threading.Thread(name=repr(fun), target=fun, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread


class AsyncTimeout(RuntimeError):
    pass


class AsyncResult(object):
    def __init__(self, source=None):
        self._event = threading.Event()
        self._value = None
        self._source = source
        self._time = time.time()

    def get_age(self):
        return time.time() - self._time

    def discard_result(self):
        self._time = 0

    def set_result(self, result, source=None):
        self._value = result
        if source is not None:
            self._source = source
        self._event.set()

    def has_result(self):
        return self._event.is_set()

    def get_source(self):
        return self._source

    def get_result(self, timeout=None):
        if not self._event.wait(timeout):
            raise AsyncTimeout
        if isinstance(self._value, Exception):
            raise self._value
        return self._value


class ThreadManager(object):
    def __init__(self, log):
        self._log = log
        self._threads = []
        self._shutdown_event = threading.Event()

    def shutdown_in_progress(self):
        return self._shutdown_event.is_set()

    def shutdown(self):
        self._shutdown_event.set()  # Trigger shutdown of threads

    def join(self, timeout=60):
        self.shutdown()
        for thread in self._threads:
            thread.join(timeout)

    def start_thread(self, name, daemon, fun, *args, **kwargs):
        thread = threading.Thread(name=name, target=fun, args=args, kwargs=kwargs)
        thread.daemon = daemon
        thread.start()
        self._threads.append(thread)
        return thread

    def start_continuous_thread(self, fun, thread_interval=0, *args, **kwargs):
        if thread_interval >= 0:
            self.start_thread(
                "continuous thread:" + repr(fun),
                False,
                self._continuous_thread_wrapper,
                fun,
                thread_interval=thread_interval,
                *args,
                **kwargs
            )

    def _continuous_thread_wrapper(
        self,
        fun,
        on_except=["log", "continue"],
        thread_waitfirst=False,
        thread_interval=0,
        *args,
        **kwargs
    ):
        if thread_waitfirst:
            self._shutdown_event.wait(thread_interval)
        while not self._shutdown_event.is_set():
            try:
                fun(*args, **kwargs)
            except Exception:
                if "log" in on_except:
                    self._log.exception("Exception in maintainance thread")
                if "continue" not in on_except:
                    return
            self._shutdown_event.wait(thread_interval)
