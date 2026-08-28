"""Unit tests for Git reflog parser (no backend required)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.collectors.git_parser import GitSignalType, parse_push_log_line, parse_reflog_line


def test_parse_commit():
    line = "abc1234 def5678 John Doe <j@e.com> 1690000000 +0530\tcommit: Fix login bug"
    signal = parse_reflog_line(line, default_branch="main")
    assert signal is not None
    assert signal.signal_type == GitSignalType.COMMIT
    assert signal.branch == "main"
    assert signal.commit_hash == "def5678"
    print("[OK] parse commit")


def test_parse_branch_change():
    line = "abc1234 def5678 John Doe <j@e.com> 1690000000 +0530\tcheckout: moving from main to feature/payment"
    signal = parse_reflog_line(line)
    assert signal is not None
    assert signal.signal_type == GitSignalType.BRANCH_CHANGED
    assert signal.branch == "feature/payment"
    print("[OK] parse branch change")


def test_parse_push_log():
    signal = parse_push_log_line("PUSH|feature/payment|abc123def456|origin")
    assert signal is not None
    assert signal.signal_type == GitSignalType.PUSH
    assert signal.branch == "feature/payment"
    print("[OK] parse push log")


if __name__ == "__main__":
    test_parse_commit()
    test_parse_branch_change()
    test_parse_push_log()
    print("Parser tests passed!")
