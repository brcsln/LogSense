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