from random import randint

import pytest

from clay_3dp_print import PrintFrame, PrintLayer
from clay_3dp_print.list_operations import iterate_nested_lists


def _make_n_random_ints(n=3, from_=0, to=300) -> list[int]:
    return [randint(from_, to) for _ in range(n)]


@pytest.fixture
def lists_of_print_frames(make_print_frame):
    return (
        [make_print_frame() for _ in range(2)],
        [make_print_frame() for _ in range(3)],
        [make_print_frame() for _ in range(5)],
    )


def nest_three_sequences(layer_a, layer_b, layer_c):
    return [[layer_a, layer_b], [[layer_c]]]


def test_iterate_nested_lists_yields_leaf_layers_with_ints():
    layer_a, layer_b, layer_c = [_make_n_random_ints() for _ in range(3)]

    nested = nest_three_sequences(layer_a, layer_b, layer_c)

    result = list(iterate_nested_lists(nested, int))

    assert result == [layer_a, layer_b, layer_c]


def test_iterate_nested_lists_yields_leaf_layers_with_print_frames(
    lists_of_print_frames,
):
    layer_a, layer_b, layer_c = lists_of_print_frames

    nested = nest_three_sequences(layer_a, layer_b, layer_c)

    result = list(iterate_nested_lists(nested, PrintFrame))

    assert result == [layer_a, layer_b, layer_c]


def test_iterate_nested_lists_yields_leaf_layers_with_print_layers(
    lists_of_print_frames,
):
    layer_a, layer_b, layer_c = [PrintLayer(li) for li in lists_of_print_frames]

    nested = nest_three_sequences(layer_a, layer_b, layer_c)

    result = list(iterate_nested_lists(nested, PrintFrame))

    assert result == [layer_a, layer_b, layer_c]


def test_iterate_nested_lists_single_item_nested_list(make_print_frame):
    frame = make_print_frame()
    layer = [frame]
    nested = [[layer]]

    result = list(iterate_nested_lists(nested, PrintFrame))

    assert result == [layer]


def test_iterate_nested_lists_type_error_for_str():
    with pytest.raises(TypeError, match="nested_list must be a non-string Sequence"):
        list(iterate_nested_lists([[["test"]]], int))


def test_iterate_nested_lists_type_error_for_non_list():
    with pytest.raises(TypeError, match="nested_list must be a Sequence"):
        list(iterate_nested_lists(4, int))
