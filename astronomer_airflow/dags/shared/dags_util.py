import re


def parse_gs_uri(uri: str):
    m = re.match(r"^gs://([^/]+)(?:/(.*))?$", uri)
    if not m:
        raise ValueError(f"Invalid GCS URI: {uri}")
    bucket, obj = m.group(1), m.group(2) or ""
    return bucket, obj