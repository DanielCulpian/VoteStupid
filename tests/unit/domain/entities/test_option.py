import pytest

from app.domain.entities.option import Option

def test_create_valid_option():
    option = Option(text="Ir al cine")

    assert option.text == "Ir al cine"
    assert option.id is not None


def test_option_rejects_empty_text():
    with pytest.raises(ValueError):
        Option(text="   ")