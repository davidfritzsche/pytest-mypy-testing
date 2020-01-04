import pytest


@pytest.mark.mypy_testing
def test_invalid_assginment():
    """An example test function to be both executed and mypy-tested"""
    foo = "abc"
    foo = 123  # E: Incompatible types in assignment (expression has type "int", variable has type "str")
    assert foo == 123
    reveal_type(123)  # R: Literal[123]?
