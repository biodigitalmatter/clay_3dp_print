from collections.abc import Iterator

import compas_rrc as rrc
from compas_fab.backends.ros.messages import ROSmsg


def stream_in_batches(
    abb: rrc.AbbClient,
    cmd_generator: Iterator[ROSmsg],
    batch_size: int = 100,
    feedback_timeout: float = 0.1,
) -> None:
    """Stream commands in batches.

    After each batch, wait for all feedback requested by commands in that batch
    before sending the next batch. Commands without feedback are
    fire-and-forget; if no commands request feedback, the whole generator is
    streamed batch by batch without waiting.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")

    futures = []
    exhausted = False

    def send_next() -> bool:
        """Send one command from the generator.

        Returns False when the generator is exhausted.
        Commands without feedback are still sent, but do not produce futures.
        """
        nonlocal exhausted

        try:
            cmd = next(cmd_generator)
        except StopIteration:
            exhausted = True
            return False

        feedback = abb.send(cmd)
        if feedback:
            futures.append(feedback)

        return True

    def send_batch() -> None:
        """Send batch_size commands, stop early if the generator is exhausted."""
        for _ in range(batch_size):
            if not send_next():
                break

    send_batch()

    # run until all commands have been sent and all requested feedback has
    # arrived.
    while not exhausted or futures:
        completed = []

        for f in futures:
            try:
                f.result(timeout=feedback_timeout)
                completed.append(f)
            except rrc.TimeoutException:
                continue

        for f in completed:
            futures.remove(f)

        if not futures:
            # feedback acts as a batch barrier.
            send_batch()
