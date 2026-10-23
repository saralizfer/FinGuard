from finguard.translations import TEXT


def test_every_interface_key_has_both_languages():
    assert TEXT["en"].keys() == TEXT["es"].keys()
    assert len(TEXT["en"]["tabs"]) == len(TEXT["es"]["tabs"]) == 5
