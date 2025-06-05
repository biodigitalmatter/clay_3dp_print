import pytest

from clay_3dp_print import PrintFrame


def test_print_frame_serializes_with_extrusion_factor(make_frame):
    frame = make_frame(1, 2, 3)
    print_frame = PrintFrame(frame, extrusion_factor=0.75)

    data = print_frame.__data__

    assert data["point"] == frame.__data__["point"]
    assert data["xaxis"] == frame.__data__["xaxis"]
    assert data["yaxis"] == frame.__data__["yaxis"]
    assert data["extrusion_factor"] == 0.75


@pytest.mark.xfail(reason="PrintFrame.copy() does not preserve extrusion_factor yet")
def test_print_frame_copy_preserves_extrusion_factor(make_frame):
    frame = make_frame(1, 2, 3)
    print_frame = PrintFrame(frame, extrusion_factor=0.75)

    copied = print_frame.copy()

    assert isinstance(copied, PrintFrame)
    assert copied is not print_frame
    assert copied.point == print_frame.point
    assert copied.xaxis == print_frame.xaxis
    assert copied.yaxis == print_frame.yaxis
    assert copied.extrusion_factor == print_frame.extrusion_factor


@pytest.mark.xfail(
    reason="PrintFrame deserialization/copy support is not fully implemented yet"
)
def test_print_frame_from_data_roundtrip(make_frame):
    frame = make_frame(1, 2, 3)
    print_frame = PrintFrame(frame, extrusion_factor=0.75)

    reconstructed = PrintFrame.__from_data__(print_frame.__data__)

    assert isinstance(reconstructed, PrintFrame)
    assert reconstructed.point == print_frame.point
    assert reconstructed.xaxis == print_frame.xaxis
    assert reconstructed.yaxis == print_frame.yaxis
    assert reconstructed.extrusion_factor == print_frame.extrusion_factor
