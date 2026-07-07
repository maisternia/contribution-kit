from contribution import __all__


def test_public_symbols_are_importable() -> None:
    namespace = __import__("contribution", fromlist=list(__all__))
    for symbol in __all__:
        assert hasattr(namespace, symbol)
