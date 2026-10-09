from io import BytesIO

from backend.services.parser import parse_log


def test_parser_counts_errors_and_warnings():
    log_data = (
        b"2026-07-18 10:00:10 INFO [payment] Request received\n"
        b"2026-07-18 10:00:14 WARNING [payment] Response time increased\n"
        b"2026-07-18 10:00:18 ERROR [database] Connection failed\n"
    )

    result = parse_log(BytesIO(log_data))

    assert result["total_lines"] == 3
    assert result["warnings"] == 1
    assert result["errors"] == 1
    assert result["first_abnormal_severity"] == "WARNING"


def test_parser_handles_normal_logs():
    log_data = (
        b"2026-07-18 10:00:10 INFO [payment] Request received\n"
        b"2026-07-18 10:00:11 DEBUG [payment] Processing request\n"
        b"2026-07-18 10:00:12 INFO [payment] Request completed\n"
    )

    result = parse_log(BytesIO(log_data))

    assert result["total_lines"] == 3
    assert result["errors"] == 0
    assert result["warnings"] == 0
    assert result["first_abnormal_line"] is None


def test_correlates_nearby_abnormal_events():
    log_data = (
        b"2026-07-18 10:14:00 WARNING [payment] Slow response\n"
        b"2026-07-18 10:15:00 ERROR [database] Connection timeout\n"
        b"2026-07-18 10:20:00 ERROR [checkout] Payment failed\n"
    )

    result = parse_log(BytesIO(log_data))

    groups = result["correlation_groups"]

    assert len(groups) == 1
    assert len(groups[0]) == 2