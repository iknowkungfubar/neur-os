from json import loads


def unwrap(response):
    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        if isinstance(data, dict) and data.get("ok") and "data" in data:
            return data["data"]
        return data
    try:
        return loads(response.text)
    except Exception:
        return {"raw": response.text}
