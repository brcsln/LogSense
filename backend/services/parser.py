import re


LOG_PATTERN = re.compile(
    r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r"\s+(?P<severity>CRITICAL|ERROR|WARNING|INFO|DEBUG)"
    r"\s+\[(?P<component>[^\]]+)\]"
    r"\s+(?P<message>.+)$"
)

RECOVERY_KEYWORDS = {
    "RECOVERED",
    "RESTORED",
    "HEALTHY",
    "SUCCESSFUL",
    "CONNECTED",
}


def parse_log(file):
    result = {
        "total_lines": 0,
        "errors": 0,
        "warnings": 0,
        "info": 0,
        "debug": 0,
        "critical": 0,
        "first_abnormal_line": None,
        "first_abnormal_severity": None,
        "first_abnormal_time": None,
        "first_abnormal_component": None,
        "first_abnormal_message": None,
        "incident_story": [],
    }

    incident_started = False

    for raw_line in file:
        line = raw_line.decode("utf-8", errors="replace").strip()

        if not line:
            continue

        result["total_lines"] += 1

        event = extract_event(line)

        if event is None:
            continue

        severity = event["severity"]
        message_upper = event["message"].upper()

        if severity == "CRITICAL":
            result["critical"] += 1
        elif severity == "ERROR":
            result["errors"] += 1
        elif severity == "WARNING":
            result["warnings"] += 1
        elif severity == "INFO":
            result["info"] += 1
        elif severity == "DEBUG":
            result["debug"] += 1

        is_abnormal = severity in {"CRITICAL", "ERROR", "WARNING"}
        is_recovery = any(
            keyword in message_upper
            for keyword in RECOVERY_KEYWORDS
        )

        if is_abnormal:
            incident_started = True

            if result["first_abnormal_line"] is None:
                save_first_abnormal(result, line, event)

            result["incident_story"].append(event)

        elif incident_started and is_recovery:
            recovery_event = event.copy()
            recovery_event["event_type"] = "RECOVERY"
            result["incident_story"].append(recovery_event)

    return result


def extract_event(line):
    match = LOG_PATTERN.match(line)

    if not match:
        return None

    return {
        "time": match.group("time"),
        "severity": match.group("severity"),
        "component": match.group("component"),
        "message": match.group("message"),
        "event_type": "LOG_EVENT",
    }


def save_first_abnormal(result, line, event):
    result["first_abnormal_line"] = line
    result["first_abnormal_severity"] = event["severity"]
    result["first_abnormal_time"] = event["time"]
    result["first_abnormal_component"] = event["component"]
    result["first_abnormal_message"] = event["message"]