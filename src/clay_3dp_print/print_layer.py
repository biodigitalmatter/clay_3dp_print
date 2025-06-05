import typing
from collections import UserList

import compas.geometry

from clay_3dp_print.print_frame import PrintFrame


class PrintLayer(UserList[PrintFrame]):
    def __init__(self, print_frames: list[PrintFrame] | None = None):
        super().__init__(initlist=print_frames)

    @classmethod
    def from_frames_and_factors(
        cls, frames: list[compas.geometry.Frame], extrusion_factors: list[float]
    ) -> typing.Self:
        return cls(
            [PrintFrame(f, ef) for f, ef in zip(frames, extrusion_factors, strict=True)]
        )

    @classmethod
    def from_frames_and_factor(
        cls, frames: list[compas.geometry.Frame], extrusion_factor: float = 1.0
    ) -> typing.Self:
        return cls([PrintFrame(f, extrusion_factor=extrusion_factor) for f in frames])
