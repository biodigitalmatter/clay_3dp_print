import numbers
import os
import pathlib
import sys
from collections.abc import Sequence

import compas.geometry
from compas.data import json_load

from clay_3dp_print import PrintLayer
from clay_3dp_print.list_operations import iterate_nested_lists


def print_layers_from_frames_and_extrusion_factors(
    frames: Sequence[compas.geometry.Frame],
    extrusion_factors: list[float] | None = None,
) -> list[PrintLayer]:
    frame_layers = list(iterate_nested_lists(frames, compas.geometry.Frame))

    if extrusion_factors is None:
        return [
            PrintLayer.from_frames_and_factor(frame_layer, 1.0)
            for frame_layer in frame_layers
        ]

    if isinstance(extrusion_factors, (str, bytes)):
        raise TypeError(
            "extrusion_factors must be a nested sequence matching frames, or None"
        )

    extrusion_factor_layers = list(
        iterate_nested_lists(extrusion_factors, numbers.Real)
    )

    return [
        PrintLayer.from_frames_and_factors(frame_layer, extrusion_factor_layer)
        for frame_layer, extrusion_factor_layer in zip(
            frame_layers,
            extrusion_factor_layers,
            strict=True,
        )
    ]


def load_print_layers_from_compas_json_dump(path: os.PathLike[str]):
    data = json_load(path)

    frames = data["frames"]
    extrusion_factors = data.get("extrusion_factors")

    return print_layers_from_frames_and_extrusion_factors(
        frames,
        extrusion_factors,
    )


def load_json_from_arg1() -> list[PrintLayer]:
    return load_print_layers_from_compas_json_dump(pathlib.Path(sys.argv[1]))
