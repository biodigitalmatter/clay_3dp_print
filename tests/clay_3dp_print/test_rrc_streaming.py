from abc import ABC, abstractmethod

import compas_rrc as rrc
from compas_fab.backends.ros.messages import ROSmsg

from clay_3dp_print.rrc_streaming import stream_in_batches


class FakeAbbClient:
    def __init__(self):
        self.sent: list[str] = []

    def send(self, cmd: "FakeCommand"):
        self.sent.append(cmd.instruction)
        return cmd.future


class FakeFuture(ABC):
    @abstractmethod
    def result(self, timeout: float | None = None):
        raise NotImplementedError()


class DelayedFuture(FakeFuture):
    """Fake feedback future that completes after N result() calls."""

    def __init__(self, complete_after_attempts: int = 1):
        self.complete_after_attempts = complete_after_attempts
        self.attempts = 0

    def result(self, timeout: float | None = None):
        self.attempts += 1

        if self.attempts < self.complete_after_attempts:
            raise rrc.TimeoutException()

        return None


class InspectingFuture(FakeFuture):
    """Fake feedback future that verifies no next batch was sent too early."""

    def __init__(self, abb: FakeAbbClient, expected_sent_before_completion: list[str]):
        self.abb: FakeAbbClient = abb
        self.expected_sent_before_completion: list[str] = (
            expected_sent_before_completion
        )
        self.attempts: int = 0

    def result(self, timeout: float | None = None):
        self.attempts += 1

        if self.attempts == 1:
            assert self.abb.sent == self.expected_sent_before_completion
            raise rrc.TimeoutException()

        return None


class RrcMsgStub(ROSmsg):
    def __init__(
        self,
        instruction: str,
        string_values: list[str] | None,
        float_values: list[float] | None,
        feedback_level=rrc.FeedbackLevel.NONE,
    ):
        self.instruction = instruction
        self.feedback_level = feedback_level
        self.exec_level = rrc.ExecutionLevel.ROBOT
        self.string_values = string_values or []
        self.float_values = float_values or []


class FakeCommand:
    def __init__(
        self,
        instruction: str,
        future: FakeFuture | None = None,
    ):
        self.instruction = instruction
        self.future = future


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

    future = DelayedFuture(complete_after_attempts=2)

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

    future = DelayedFuture(complete_after_attempts=1)

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

    future = InspectingFuture(
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
