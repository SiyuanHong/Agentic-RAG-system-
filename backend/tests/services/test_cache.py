import struct

from app.services.cache import _floats_to_bytes


def test_floats_to_bytes():
    vec = [1.0, 2.0, 3.0]
    result = _floats_to_bytes(vec)
    expected = struct.pack("3f", 1.0, 2.0, 3.0)
    assert result == expected


def test_floats_to_bytes_empty():
    result = _floats_to_bytes([])
    assert result == b""
