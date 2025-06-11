"""Tests for the command-line interface argument parsing."""
import pytest
from vhf_watch.cli import parse_args

def test_parse_args_defaults():
    """Test parsing with no arguments, expecting defaults."""
    args = parse_args([])
    assert args.debug is False
    assert args.duration == 0  # Default is 0 for continuous
    assert args.chunk == 10    # Default chunk is 10 seconds

def test_parse_args_short_options():
    """Test parsing with short options."""
    args = parse_args(["-d", "-t", "30", "-c", "15"])
    assert args.debug is True
    assert args.duration == 30
    assert args.chunk == 15

def test_parse_args_long_options():
    """Test parsing with long options."""
    args = parse_args(["--debug", "--duration", "60", "--chunk", "5"])
    assert args.debug is True
    assert args.duration == 60
    assert args.chunk == 5

def test_parse_args_mixed_options():
    """Test parsing with a mix of short and long options and different values."""
    args = parse_args(["-d", "--duration", "120"])
    assert args.debug is True
    assert args.duration == 120
    assert args.chunk == 10  # Default chunk

    args = parse_args(["--chunk", "20"])
    assert args.debug is False # Default debug
    assert args.duration == 0   # Default duration
    assert args.chunk == 20

# Example of testing invalid input, though argparse handles this by exiting.
# To test this, you'd need to capture SystemExit.
# def test_parse_args_invalid_duration(capsys):
#     with pytest.raises(SystemExit):
#         parse_args(["--duration", "abc"])
#     # captured = capsys.readouterr()
#     # assert "invalid int value" in captured.err

if __name__ == '__main__':
    pytest.main()
