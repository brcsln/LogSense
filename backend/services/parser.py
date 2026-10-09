import re
from datetime import datetime

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
        "incident_summary": {
            "started_at": None,
            "component": None,
            "severity": None,
            "status": "Healthy",
        },
        "component_summary": {},
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

            event["event_type"] = classify_event(event, incident_started)
            component = event["component"]

            if component:
             result["component_summary"][component] = (
                result["component_summary"].get(component, 0) + 1
        )

            if result["first_abnormal_line"] is None:
                save_first_abnormal(result, line, event)

            incident_started = True

            result["incident_story"].append(event)

        elif incident_started and is_recovery:
            recovery_event = event.copy()
            recovery_event["event_type"] = "RECOVERY"

            result["incident_story"].append(recovery_event)

            result["incident_summary"]["status"] = "Recovered"

    
    
    result["correlation_groups"] = correlate_events(
         result["incident_story"]
    )

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

    result["incident_summary"]["started_at"] = event["time"]
    result["incident_summary"]["component"] = event["component"]
    result["incident_summary"]["severity"] = event["severity"]
    result["incident_summary"]["status"] = "Degraded"

def classify_event(event, incident_started):
    """
    Classify an event into a meaningful investigation stage.
    """

    severity = event["severity"]

    if not incident_started:
        return "INCIDENT_START"

    if severity in {"ERROR", "CRITICAL"}:
        return "FAILURE"

    return "WARNING"


def correlate_events(incident_story, window_seconds=120):
    related_groups = []
    current_group = []

    abnormal_events = [
        event for event in incident_story
        if event["severity"] in {"WARNING", "ERROR", "CRITICAL"}
    ]

    abnormal_events.sort(key=lambda event: event["time"])

    for event in abnormal_events:
        if not current_group:
            current_group.append(event)
            continue

        first_time = datetime.fromisoformat(current_group[0]["time"])
        event_time = datetime.fromisoformat(event["time"])

        difference = (event_time - first_time).total_seconds()

        if difference <= window_seconds:
            current_group.append(event)
        else:
            if len(current_group) >= 2:
                related_groups.append(current_group)

            current_group = [event]

    if len(current_group) >= 2:
        related_groups.append(current_group)

    return related_groups

    