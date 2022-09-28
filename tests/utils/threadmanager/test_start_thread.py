from tinybt.utils.threadmanager import start_thread


def test_start_thread():

    mutated = {"value": 1}

    def mutator(amount):
        mutated["value"] += amount

    thread = start_thread(mutator, amount=10)
    thread.join()

    assert mutated["value"] == 11
