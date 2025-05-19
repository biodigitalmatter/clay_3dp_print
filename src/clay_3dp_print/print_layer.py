import typing
from collections import UserList

from clay_3dp_print.print_frame import PrintFrame


class PrintLayer(UserList):
    def __init__(self, print_frames: list[PrintFrame] | None = None):
        self.data = print_frames or []

    @classmethod
    def from_frames_and_factors(cls, frames, extrusion_factors) -> typing.Self:
        return cls(
            [PrintFrame(f, ef) for f, ef in zip(frames, extrusion_factors, strict=True)]
        )
