import pytest
from compas.geometry import Frame

from clay_3dp_print import PrintFrame


@pytest.fixture
def make_frame():
    def _make_frame(x=0, y=0, z=0) -> Frame:
        return Frame(point=[x, y, z])

    return _make_frame


@pytest.fixture
def make_print_frame(make_frame):
    def _make_print_frame(x=0, y=0, z=0, e=0) -> PrintFrame:
        return PrintFrame(make_frame(x, y, z), e)

    return _make_print_frame
