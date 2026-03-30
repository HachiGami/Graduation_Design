import json
import requests


BASE_URL = "http://127.0.0.1:8000/api/analytics/risks"


def call_api(params=None):
    response = requests.get(BASE_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def print_result(title, payload):
    print(f"\n=== {title} ===")
    print(f"风险总数: {len(payload)}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main():
    all_risks = call_api()
    print_result("全域风险", all_risks)

    domain_risks = call_api({"domain": "处理"})
    print_result("domain=处理 风险", domain_risks)


if __name__ == "__main__":
    main()
