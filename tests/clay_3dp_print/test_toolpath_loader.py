from compas.data import json_dump

from clay_3dp_print.toolpath_loader import (
    load_print_layers_from_compas_json_dump,
    print_layers_from_frames_and_extrusion_factors,
)


def test_print_layers_from_frames_uses_default_extrusion_factor(make_frame):
    layer_a = [make_frame(0, 0, 0), make_frame(1, 0, 0)]
    layer_b = [make_frame(0, 1, 0)]

    frames = [[layer_a], [layer_b]]

    result = print_layers_from_frames_and_extrusion_factors(frames)

    assert len(result) == 2
    assert [pf.extrusion_factor for pf in result[0]] == [1.0, 1.0]
    assert [pf.extrusion_factor for pf in result[1]] == [1.0]


def test_print_layers_from_frames_and_extrusion_factors(make_frame):
    layer_a = [make_frame(0, 0, 0), make_frame(1, 0, 0)]
    layer_b = [make_frame(0, 1, 0)]

    frames = [[layer_a], [layer_b]]
    extrusion_factors = [[[0.5, 0.75]], [[1.25]]]

    result = print_layers_from_frames_and_extrusion_factors(
        frames,
        extrusion_factors,
    )

    assert len(result) == 2
    assert [pf.extrusion_factor for pf in result[0]] == [0.5, 0.75]
    assert [pf.extrusion_factor for pf in result[1]] == [1.25]


def test_load_print_layers_from_json(tmp_path, make_frame):
    filepath = tmp_path / "toolpath.json"

    data = {
        "frames": [
            [
                [make_frame(0, 0, 0), make_frame(1, 0, 0)],
            ]
        ],
        "extrusion_factors": [
            [
                [0.5, 0.75],
            ]
        ],
    }

    json_dump(data, filepath)

    result = load_print_layers_from_compas_json_dump(filepath)

    assert len(result) == 1
    assert [pf.extrusion_factor for pf in result[0]] == [0.5, 0.75]
