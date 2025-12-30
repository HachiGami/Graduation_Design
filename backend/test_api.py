import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    response = requests.get(f"{BASE_URL}/")
    print("Health Check:", response.json())

def test_init_demo_data():
    response = requests.post(f"{BASE_URL}/api/demo/init")
    print("Init Demo Data:", response.json())

def test_get_resources():
    response = requests.get(f"{BASE_URL}/api/resources")
    print(f"Resources Count: {len(response.json())}")

def test_get_personnel():
    response = requests.get(f"{BASE_URL}/api/personnel")
    print(f"Personnel Count: {len(response.json())}")

def test_get_dependencies():
    response = requests.get(f"{BASE_URL}/api/dependencies")
    print(f"Dependencies Count: {len(response.json())}")

def test_get_activities():
    response = requests.get(f"{BASE_URL}/api/activities")
    print(f"Activities Count: {len(response.json())}")

if __name__ == "__main__":
    print("Testing API...")
    try:
        test_health()
        print("\nInitializing demo data...")
        test_init_demo_data()
        print("\nTesting endpoints...")
        test_get_resources()
        test_get_personnel()
        test_get_dependencies()
        test_get_activities()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"Error: {e}")

