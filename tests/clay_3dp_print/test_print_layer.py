from clay_3dp_print import PrintFrame, PrintLayer


def test_print_layer_from_frames_and_factors(make_frame):
    frames = [make_frame(0, 0, 0), make_frame(1, 2, 3)]
    extrusion_factors = [0.5, 1.5]

    layer = PrintLayer.from_frames_and_factors(frames, extrusion_factors)

    assert isinstance(layer, PrintLayer)
    assert len(layer) == 2
    assert all(isinstance(print_frame, PrintFrame) for print_frame in layer)
    assert [print_frame.extrusion_factor for print_frame in layer] == extrusion_factors
