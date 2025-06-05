from collections.abc import Sequence
from typing import Iterator, Type, TypeVar

T = TypeVar("T")


def iterate_nested_lists(nested_list: Sequence, match_type: Type) -> Iterator[Sequence]:
    if isinstance(nested_list, (str, bytes)):
        raise TypeError("nested_list must be a non-string Sequence")

    if not isinstance(nested_list, Sequence):
        raise TypeError(
            f"nested_list must be a Sequence, got {type(nested_list).__name__}"
        )

    if not nested_list:
        return

    if isinstance(nested_list[0], match_type):
        yield nested_list
        return

    for item in nested_list:
        if isinstance(item, Sequence):
            yield from iterate_nested_lists(item, match_type)
