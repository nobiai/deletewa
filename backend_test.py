#!/usr/bin/env python3
"""
Backend API Testing for WhatsApp Deleted Messages Monitor
Tests all backend endpoints with proper error handling and validation
"""

import requests
import json
from datetime import datetime
import sys
import os

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    base_url = line.split('=')[1].strip()
                    return f"{base_url}/api"
        return "https://message-rescue-1.preview.emergentagent.com/api"
    except:
        return "https://message-rescue-1.preview.emergentagent.com/api"

BASE_URL = get_backend_url()
print(f"Testing backend at: {BASE_URL}")

class BackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = {}
        
    def log_test(self, test_name, success, message, response_data=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results[test_name] = {
            'success': success,
            'message': message,
            'response_data': response_data
        }
        
        if response_data and not success:
            print(f"   Response: {json.dumps(response_data, indent=2)}")
    
    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                if "WhatsApp Deleted Messages Monitor API" in data.get("message", ""):
                    self.log_test("Root Endpoint", True, "API is accessible and responding correctly", data)
                    return True
                else:
                    self.log_test("Root Endpoint", False, f"Unexpected response message: {data}", data)
                    return False
            else:
                self.log_test("Root Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Connection error: {str(e)}")
            return False
    
    def test_sample_data_initialization(self):
        """Test POST /api/init-sample-data endpoint"""
        try:
            response = self.session.post(f"{self.base_url}/init-sample-data")
            if response.status_code == 200:
                data = response.json()
                expected_messages = ["Sample data initialized successfully", "Sample data already exists"]
                if any(msg in data.get("message", "") for msg in expected_messages):
                    self.log_test("Sample Data Initialization", True, f"Sample data endpoint working: {data['message']}", data)
                    return True
                else:
                    self.log_test("Sample Data Initialization", False, f"Unexpected response: {data}", data)
                    return False
            else:
                self.log_test("Sample Data Initialization", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Sample Data Initialization", False, f"Request error: {str(e)}")
            return False
    
    def test_chat_management_api(self):
        """Test GET /api/chats endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/chats")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        # Validate chat structure
                        chat = data[0]
                        required_fields = ['id', 'name', 'chat_type', 'participants', 'deleted_messages_count']
                        missing_fields = [field for field in required_fields if field not in chat]
                        
                        if not missing_fields:
                            self.log_test("Chat Management API", True, f"Retrieved {len(data)} chats with proper structure", {"chat_count": len(data), "sample_chat": chat})
                            return True
                        else:
                            self.log_test("Chat Management API", False, f"Missing required fields: {missing_fields}", data)
                            return False
                    else:
                        self.log_test("Chat Management API", False, "No chats found - sample data may not be initialized", data)
                        return False
                else:
                    self.log_test("Chat Management API", False, f"Expected list, got: {type(data)}", data)
                    return False
            else:
                self.log_test("Chat Management API", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Chat Management API", False, f"Request error: {str(e)}")
            return False
    
    def test_message_management_api(self):
        """Test GET /api/messages endpoint"""
        try:
            # Test getting all messages
            response = self.session.get(f"{self.base_url}/messages")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        # Validate message structure
                        message = data[0]
                        required_fields = ['id', 'chat_id', 'sender_name', 'content', 'status', 'timestamp']
                        missing_fields = [field for field in required_fields if field not in message]
                        
                        if not missing_fields:
                            self.log_test("Message Management API", True, f"Retrieved {len(data)} messages with proper structure", {"message_count": len(data), "sample_message": message})
                            
                            # Test filtering by chat_id if we have messages
                            if len(data) > 0:
                                chat_id = data[0]['chat_id']
                                filter_response = self.session.get(f"{self.base_url}/messages?chat_id={chat_id}")
                                if filter_response.status_code == 200:
                                    filtered_data = filter_response.json()
                                    self.log_test("Message Filtering by Chat ID", True, f"Retrieved {len(filtered_data)} messages for chat {chat_id}")
                                else:
                                    self.log_test("Message Filtering by Chat ID", False, f"HTTP {filter_response.status_code}")
                            
                            return True
                        else:
                            self.log_test("Message Management API", False, f"Missing required fields: {missing_fields}", data)
                            return False
                    else:
                        self.log_test("Message Management API", True, "No messages found (empty database)", data)
                        return True
                else:
                    self.log_test("Message Management API", False, f"Expected list, got: {type(data)}", data)
                    return False
            else:
                self.log_test("Message Management API", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Message Management API", False, f"Request error: {str(e)}")
            return False
    
    def test_deleted_messages_api(self):
        """Test GET /api/messages/deleted endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/messages/deleted")
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        # Validate deleted message structure
                        deleted_msg = data[0]
                        required_fields = ['id', 'chat_id', 'sender_name', 'content', 'status', 'deleted_at']
                        missing_fields = [field for field in required_fields if field not in deleted_msg]
                        
                        # Check if status is 'deleted'
                        if deleted_msg.get('status') != 'deleted':
                            self.log_test("Deleted Messages API", False, f"Message status should be 'deleted', got: {deleted_msg.get('status')}", data)
                            return False
                        
                        if not missing_fields:
                            # Check if messages are sorted by deletion timestamp (most recent first)
                            if len(data) > 1:
                                first_deleted = data[0].get('deleted_at')
                                second_deleted = data[1].get('deleted_at')
                                if first_deleted and second_deleted and first_deleted < second_deleted:
                                    self.log_test("Deleted Messages Sorting", False, "Messages not sorted by deletion timestamp (desc)", {"first": first_deleted, "second": second_deleted})
                                else:
                                    self.log_test("Deleted Messages Sorting", True, "Messages properly sorted by deletion timestamp")
                            
                            self.log_test("Deleted Messages API", True, f"Retrieved {len(data)} deleted messages with proper structure", {"deleted_count": len(data), "sample_deleted": deleted_msg})
                            return True
                        else:
                            self.log_test("Deleted Messages API", False, f"Missing required fields: {missing_fields}", data)
                            return False
                    else:
                        self.log_test("Deleted Messages API", True, "No deleted messages found", data)
                        return True
                else:
                    self.log_test("Deleted Messages API", False, f"Expected list, got: {type(data)}", data)
                    return False
            else:
                self.log_test("Deleted Messages API", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Deleted Messages API", False, f"Request error: {str(e)}")
            return False
    
    def test_statistics_api(self):
        """Test GET /api/stats endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/stats")
            if response.status_code == 200:
                data = response.json()
                required_fields = ['total_deleted', 'today_deleted', 'this_week_deleted', 'most_active_chat']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Validate data types
                    if (isinstance(data['total_deleted'], int) and 
                        isinstance(data['today_deleted'], int) and 
                        isinstance(data['this_week_deleted'], int)):
                        
                        # Check logical consistency
                        if (data['today_deleted'] <= data['this_week_deleted'] <= data['total_deleted']):
                            self.log_test("Statistics API", True, f"Stats retrieved with proper structure and logical consistency", data)
                            return True
                        else:
                            self.log_test("Statistics API", False, f"Illogical stats: today({data['today_deleted']}) > week({data['this_week_deleted']}) > total({data['total_deleted']})", data)
                            return False
                    else:
                        self.log_test("Statistics API", False, f"Invalid data types in stats response", data)
                        return False
                else:
                    self.log_test("Statistics API", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_test("Statistics API", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Statistics API", False, f"Request error: {str(e)}")
            return False
    
    def test_data_models_validation(self):
        """Test data models by creating a test message and validating response structure"""
        try:
            # First get a chat to use for testing
            chats_response = self.session.get(f"{self.base_url}/chats")
            if chats_response.status_code != 200:
                self.log_test("Data Models Validation", False, "Cannot test models - chats endpoint failed")
                return False
            
            chats = chats_response.json()
            if not chats:
                self.log_test("Data Models Validation", False, "Cannot test models - no chats available")
                return False
            
            chat_id = chats[0]['id']
            
            # Create a test message
            test_message = {
                "chat_id": chat_id,
                "sender_name": "Test User",
                "sender_phone": "+1234567890",
                "content": "This is a test message for model validation",
                "message_type": "text"
            }
            
            response = self.session.post(f"{self.base_url}/messages", json=test_message)
            if response.status_code == 200:
                data = response.json()
                
                # Validate UUID format for id field
                import re
                uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                if not re.match(uuid_pattern, data.get('id', '')):
                    self.log_test("Data Models Validation", False, f"Invalid UUID format for message ID: {data.get('id')}", data)
                    return False
                
                # Validate timestamp format
                timestamp = data.get('timestamp')
                if timestamp:
                    try:
                        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except ValueError:
                        self.log_test("Data Models Validation", False, f"Invalid timestamp format: {timestamp}", data)
                        return False
                
                # Validate required fields are present
                required_fields = ['id', 'chat_id', 'sender_name', 'content', 'status', 'timestamp']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test("Data Models Validation", True, "Message model validation successful - UUID, timestamp, and required fields present", data)
                    return True
                else:
                    self.log_test("Data Models Validation", False, f"Missing required fields: {missing_fields}", data)
                    return False
            else:
                self.log_test("Data Models Validation", False, f"Failed to create test message: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Data Models Validation", False, f"Model validation error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests in the correct order"""
        print("=" * 60)
        print("WHATSAPP DELETED MESSAGES BACKEND API TESTING")
        print("=" * 60)
        
        tests = [
            ("Root Endpoint", self.test_root_endpoint),
            ("Sample Data Initialization", self.test_sample_data_initialization),
            ("Chat Management API", self.test_chat_management_api),
            ("Message Management API", self.test_message_management_api),
            ("Deleted Messages API", self.test_deleted_messages_api),
            ("Statistics API", self.test_statistics_api),
            ("Data Models Validation", self.test_data_models_validation),
        ]
        
        results = {}
        for test_name, test_func in tests:
            print(f"\n--- Testing {test_name} ---")
            results[test_name] = test_func()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All backend tests passed!")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed")
            return False

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)