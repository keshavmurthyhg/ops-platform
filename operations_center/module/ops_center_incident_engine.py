from collections import Counter


def detect_critical_failures(
    failure_data
):

    server_counts = Counter()

    for row in failure_data:

        server = row.get(
            "Windchill Server",
            ""
        )

        server_counts[server] += 1

    critical_servers = [
        server
        for server, count
        in server_counts.items()
        if count >= 3
    ]

    return critical_servers