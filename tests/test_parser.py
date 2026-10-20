from io import BytesIO

from backend.services.parser import parse_log, correlate_by_request_id


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


def test_extracts_request_id():
    from backend.services.parser import extract_event

    line = "2026-07-18 10:14:00 ERROR [payment] Payment failed request_id=456"

    event = extract_event(line)

    assert event["request_id"] == "456"

def test_correlates_matching_request_ids():
    log_data = (
        b"2026-07-18 10:00:00 ERROR [payment] Failed request_id=123\n"
        b"2026-07-18 10:05:00 ERROR [database] Timeout request_id=123\n"
    )

    result = parse_log(BytesIO(log_data))

    assert len(result["correlation_groups"]) == 1
    assert len(result["correlation_groups"][0]) == 2

def test_multiple_request_ids_in_group():
    log_data = (
        b"2026-07-18 10:00:00 ERROR [payment] Failed request_id=123\n"
        b"2026-07-18 10:01:00 ERROR [database] Timeout request_id=456\n"
        b"2026-07-18 10:05:00 ERROR [checkout] Failed request_id=456\n"
    )

    result = parse_log(BytesIO(log_data))

    assert len(result["correlation_groups"]) == 1
    assert len(result["correlation_groups"][0]) == 3


def test_groups_events_by_request_id():
    events = [
        {"request_id": "123", "component": "payment"},
        {"request_id": "123", "component": "database"},
    ]

    groups = correlate_by_request_id(events)

    assert len(groups["123"]) == 2