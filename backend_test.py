import requests
import sys
import os
import base64
from datetime import datetime
from io import BytesIO
from PIL import Image

class AttendanceSystemTester:
    def __init__(self, base_url="https://smartroster.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_student_id = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def create_test_image(self):
        """Create a simple test image for face upload"""
        # Create a simple 200x200 RGB image
        img = Image.new('RGB', (200, 200), color='lightblue')
        
        # Save to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        return img_bytes

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = requests.get(f"{self.api_url}/")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                details += f", Response: {response.json()}"
            return self.log_test("Root Endpoint", success, details)
        except Exception as e:
            return self.log_test("Root Endpoint", False, f"Error: {str(e)}")

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        try:
            response = requests.get(f"{self.api_url}/dashboard/stats")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                required_fields = ['total_students', 'present_today', 'attendance_rate', 'active_classes']
                has_all_fields = all(field in data for field in required_fields)
                success = success and has_all_fields
                details += f", Data: {data}"
            return self.log_test("Dashboard Stats", success, details)
        except Exception as e:
            return self.log_test("Dashboard Stats", False, f"Error: {str(e)}")

    def test_get_classes(self):
        """Test get classes endpoint"""
        try:
            response = requests.get(f"{self.api_url}/classes")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                success = 'classes' in data
                details += f", Classes: {data}"
            return self.log_test("Get Classes", success, details)
        except Exception as e:
            return self.log_test("Get Classes", False, f"Error: {str(e)}")

    def test_get_students_empty(self):
        """Test get students endpoint (should be empty initially)"""
        try:
            response = requests.get(f"{self.api_url}/students")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                success = isinstance(data, list)
                details += f", Students count: {len(data)}"
            return self.log_test("Get Students (Empty)", success, details)
        except Exception as e:
            return self.log_test("Get Students (Empty)", False, f"Error: {str(e)}")

    def test_create_student(self):
        """Test creating a new student with face image"""
        try:
            # Create test image
            test_image = self.create_test_image()
            
            # Prepare form data
            files = {
                'face_image': ('test_face.jpg', test_image, 'image/jpeg')
            }
            data = {
                'student_name': 'Test Student',
                'class_name': 'Grade 10A',
                'roll_no': 1,
                'father_name': 'Test Father'
            }
            
            response = requests.post(f"{self.api_url}/students", files=files, data=data)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                student_data = response.json()
                self.test_student_id = student_data.get('id')
                required_fields = ['id', 'student_name', 'class_name', 'roll_no', 'father_name']
                has_all_fields = all(field in student_data for field in required_fields)
                success = success and has_all_fields
                details += f", Student ID: {self.test_student_id}"
            else:
                try:
                    error_detail = response.json()
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text}"
                    
            return self.log_test("Create Student", success, details)
        except Exception as e:
            return self.log_test("Create Student", False, f"Error: {str(e)}")

    def test_get_students_with_data(self):
        """Test get students endpoint after adding a student"""
        try:
            response = requests.get(f"{self.api_url}/students")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                success = isinstance(data, list) and len(data) > 0
                details += f", Students count: {len(data)}"
                if len(data) > 0:
                    details += f", First student: {data[0].get('student_name', 'Unknown')}"
            return self.log_test("Get Students (With Data)", success, details)
        except Exception as e:
            return self.log_test("Get Students (With Data)", False, f"Error: {str(e)}")

    def test_duplicate_student(self):
        """Test creating duplicate student (should fail)"""
        try:
            # Create test image
            test_image = self.create_test_image()
            
            # Prepare form data with same roll number and class
            files = {
                'face_image': ('test_face2.jpg', test_image, 'image/jpeg')
            }
            data = {
                'student_name': 'Another Student',
                'class_name': 'Grade 10A',
                'roll_no': 1,  # Same roll number as previous test
                'father_name': 'Another Father'
            }
            
            response = requests.post(f"{self.api_url}/students", files=files, data=data)
            success = response.status_code == 400  # Should fail with 400
            details = f"Status: {response.status_code}"
            
            if response.status_code == 400:
                try:
                    error_detail = response.json()
                    details += f", Error: {error_detail}"
                except:
                    details += f", Response: {response.text}"
                    
            return self.log_test("Duplicate Student (Should Fail)", success, details)
        except Exception as e:
            return self.log_test("Duplicate Student (Should Fail)", False, f"Error: {str(e)}")

    def test_get_todays_attendance_empty(self):
        """Test get today's attendance (should be empty initially)"""
        try:
            response = requests.get(f"{self.api_url}/attendance/today")
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                success = isinstance(data, list)
                details += f", Attendance records: {len(data)}"
            return self.log_test("Get Today's Attendance (Empty)", success, details)
        except Exception as e:
            return self.log_test("Get Today's Attendance (Empty)", False, f"Error: {str(e)}")

    def test_mark_attendance(self):
        """Test marking attendance with face image"""
        try:
            # Create test image for attendance
            test_image = self.create_test_image()
            
            # Prepare form data
            files = {
                'face_image': ('attendance_face.jpg', test_image, 'image/jpeg')
            }
            data = {
                'class_name': 'Grade 10A'
            }
            
            response = requests.post(f"{self.api_url}/attendance/mark", files=files, data=data)
            success = response.status_code in [200, 404, 409]  # 200=success, 404=no match, 409=already marked
            details = f"Status: {response.status_code}"
            
            try:
                response_data = response.json()
                details += f", Response: {response_data}"
            except:
                details += f", Response: {response.text}"
                
            return self.log_test("Mark Attendance", success, details)
        except Exception as e:
            return self.log_test("Mark Attendance", False, f"Error: {str(e)}")

    def test_mark_attendance_no_class(self):
        """Test marking attendance with invalid class"""
        try:
            # Create test image for attendance
            test_image = self.create_test_image()
            
            # Prepare form data with non-existent class
            files = {
                'face_image': ('attendance_face.jpg', test_image, 'image/jpeg')
            }
            data = {
                'class_name': 'NonExistentClass'
            }
            
            response = requests.post(f"{self.api_url}/attendance/mark", files=files, data=data)
            success = response.status_code == 404  # Should fail with 404
            details = f"Status: {response.status_code}"
            
            try:
                response_data = response.json()
                details += f", Response: {response_data}"
            except:
                details += f", Response: {response.text}"
                
            return self.log_test("Mark Attendance (Invalid Class)", success, details)
        except Exception as e:
            return self.log_test("Mark Attendance (Invalid Class)", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Automated Attendance System Backend Tests")
        print("=" * 60)
        
        # Test basic endpoints
        self.test_root_endpoint()
        self.test_dashboard_stats()
        self.test_get_classes()
        self.test_get_students_empty()
        
        # Test student management
        self.test_create_student()
        self.test_get_students_with_data()
        self.test_duplicate_student()
        
        # Test attendance functionality
        self.test_get_todays_attendance_empty()
        self.test_mark_attendance()
        self.test_mark_attendance_no_class()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed! Backend is working correctly.")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed. Please check the issues above.")
            return 1

def main():
    tester = AttendanceSystemTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())