
import requests
import sys
import json
import time
from datetime import datetime

class KaizenAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, form_data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        
        if form_data:
            # Don't set Content-Type for multipart/form-data, requests will set it with boundary
            pass
        elif data and not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=form_data, headers=headers, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            
            # Try to get JSON response, but handle non-JSON responses gracefully
            try:
                response_data = response.json()
                response_preview = json.dumps(response_data, indent=2)[:500] + "..." if len(json.dumps(response_data)) > 500 else json.dumps(response_data, indent=2)
            except:
                response_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"Response: {response_preview}")
                self.test_results.append({
                    "name": name,
                    "status": "PASSED",
                    "endpoint": endpoint,
                    "response_code": response.status_code
                })
                return True, response
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response_preview}")
                self.test_results.append({
                    "name": name,
                    "status": "FAILED",
                    "endpoint": endpoint,
                    "response_code": response.status_code,
                    "error": f"Expected {expected_status}, got {response.status_code}"
                })
                return False, response

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "status": "ERROR",
                "endpoint": endpoint,
                "error": str(e)
            })
            return False, None

    def test_health_endpoint(self):
        """Test the health endpoint"""
        return self.run_test(
            "Health Endpoint",
            "GET",
            "api/health",
            200
        )

    def test_root_endpoint(self):
        """Test the root endpoint"""
        return self.run_test(
            "Root Endpoint",
            "GET",
            "api",
            200
        )

    def test_suggestions_endpoint(self):
        """Test getting suggestions"""
        return self.run_test(
            "Get Suggestions",
            "GET",
            "api/suggestions",
            200
        )

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASSED" else "❌"
            print(f"{status_icon} {result['name']}")
            if result["status"] != "PASSED":
                print(f"   Error: {result.get('error', 'Unknown error')}")
        
        print("="*50)
        return self.tests_passed == self.tests_run

def main():
    # Get the backend URL from the frontend .env file
    backend_url = "https://a7b92ab7-68e5-4594-a8ae-2cd5be2a157a.preview.emergentagent.com"
    
    print(f"Testing Kaizen Voice Recorder API at: {backend_url}")
    print("="*50)
    
    # Initialize tester
    tester = KaizenAPITester(backend_url)
    
    # Run tests
    tester.test_root_endpoint()
    tester.test_health_endpoint()
    tester.test_suggestions_endpoint()
    
    # Print summary
    success = tester.print_summary()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
