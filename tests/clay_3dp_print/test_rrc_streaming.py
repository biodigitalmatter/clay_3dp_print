import compas_rrc as rrc
from clay_3dp_print.rrc_streaming import stream_in_batches


class FakeCommand:
    def __init__(self, name, future=None):
        self.name = name
        self.future = future


class FakeAbbClient:
    def __init__(self):
        self.sent = []

    def send(self, cmd):
        self.sent.append(cmd.name)
        return cmd.future


class FakeFuture:
    def __init__(self, abb, expected_sent_before_completion):
        self.abb = abb
        self.expected_sent_before_completion = expected_sent_before_completion
        self.attempts = 0

    def result(self, timeout=None):
        self.attempts += 1

        if self.attempts == 1:
            assert self.abb.sent == self.expected_sent_before_completion
            raise rrc.TimeoutException()

        return None


def test_streams_all_commands_without_feedback():
    abb = FakeAbbClient()

    cmds = (FakeCommand(f"cmd_{i}") for i in range(5))

    stream_in_batches(abb, cmds, batch_size=2)

    assert abb.sent == [
        "cmd_0",
        "cmd_1",
        "cmd_2",
        "cmd_3",
        "cmd_4",
    ]


def test_waits_for_feedback_before_next_batch():
    abb = FakeAbbClient()

    future = FakeFuture(complete_after_attempts=2)

    cmds = (
        cmd
        for cmd in [
            FakeCommand("cmd_0"),
            FakeCommand("checkpoint", future=future),
            FakeCommand("cmd_2"),
            FakeCommand("cmd_3"),
        ]
    )

    stream_in_batches(abb, cmds, batch_size=2, feedback_timeout=0.001)

    assert abb.sent == [
        "cmd_0",
        "checkpoint",
        "cmd_2",
        "cmd_3",
    ]

    assert future.attempts == 2


def test_feedback_in_later_batch():
    abb = FakeAbbClient()

    future = FakeFuture(complete_after_attempts=1)

    cmds = (
        cmd
        for cmd in [
            FakeCommand("cmd_0"),
            FakeCommand("cmd_1"),
            FakeCommand("checkpoint", future=future),
            FakeCommand("cmd_3"),
            FakeCommand("cmd_4"),
        ]
    )

    stream_in_batches(abb, cmds, batch_size=2)

    assert abb.sent == [
        "cmd_0",
        "cmd_1",
        "checkpoint",
        "cmd_3",
        "cmd_4",
    ]

    assert future.attempts == 1


def test_does_not_send_next_batch_while_feedback_pending():
    abb = FakeAbbClient()

    future = FakeFuture(
        abb,
        expected_sent_before_completion=["cmd_0", "checkpoint"],
    )

    cmds = (
        cmd
        for cmd in [
            FakeCommand("cmd_0"),
            FakeCommand("checkpoint", future=future),
            FakeCommand("cmd_2"),
            FakeCommand("cmd_3"),
        ]
    )

    stream_in_batches(abb, cmds, batch_size=2, feedback_timeout=0.001)

    assert abb.sent == [
        "cmd_0",
        "checkpoint",
        "cmd_2",
        "cmd_3",
    ]
