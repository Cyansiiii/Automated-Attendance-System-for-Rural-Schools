import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import axios from 'axios';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Badge } from './components/ui/badge';
import { Separator } from './components/ui/separator';
import { toast, Toaster } from 'sonner';
import { Camera, Users, UserCheck, GraduationCap, Upload, CheckCircle, AlertCircle, Clock } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [dashboardStats, setDashboardStats] = useState({
    total_students: 0,
    present_today: 0,
    attendance_rate: 0,
    active_classes: []
  });
  const [students, setStudents] = useState([]);
  const [attendanceRecords, setAttendanceRecords] = useState([]);
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState('');
  const [loading, setLoading] = useState(false);
  
  // Student registration form
  const [newStudent, setNewStudent] = useState({
    student_name: '',
    class_name: '',
    roll_no: '',
    father_name: ''
  });
  const [selectedImage, setSelectedImage] = useState(null);
  
  // Attendance marking
  const [attendanceClass, setAttendanceClass] = useState('');
  const [attendanceImage, setAttendanceImage] = useState(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);

  useEffect(() => {
    fetchDashboardStats();
    fetchStudents();
    fetchTodaysAttendance();
    fetchClasses();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setDashboardStats(response.data);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    }
  };

  const fetchStudents = async () => {
    try {
      const response = await axios.get(`${API}/students`);
      setStudents(response.data);
    } catch (error) {
      console.error('Error fetching students:', error);
    }
  };

  const fetchTodaysAttendance = async () => {
    try {
      const response = await axios.get(`${API}/attendance/today`);
      setAttendanceRecords(response.data);
    } catch (error) {
      console.error('Error fetching attendance:', error);
    }
  };

  const fetchClasses = async () => {
    try {
      const response = await axios.get(`${API}/classes`);
      setClasses(response.data.classes);
    } catch (error) {
      console.error('Error fetching classes:', error);
    }
  };

  const handleStudentSubmit = async (e) => {
    e.preventDefault();
    if (!selectedImage) {
      toast.error('Please select a face image');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('student_name', newStudent.student_name);
      formData.append('class_name', newStudent.class_name);
      formData.append('roll_no', parseInt(newStudent.roll_no));
      formData.append('father_name', newStudent.father_name);
      formData.append('face_image', selectedImage);

      await axios.post(`${API}/students`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast.success('Student registered successfully!');
      setNewStudent({ student_name: '', class_name: '', roll_no: '', father_name: '' });
      setSelectedImage(null);
      fetchStudents();
      fetchDashboardStats();
      fetchClasses();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error registering student');
    }
    setLoading(false);
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
      }
    } catch (error) {
      toast.error('Error accessing camera: ' + error.message);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      setCameraActive(false);
    }
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      canvas.toBlob(blob => {
        setAttendanceImage(blob);
        toast.success('Photo captured! Click Mark Attendance to process.');
      }, 'image/jpeg', 0.8);
    }
  };

  const markAttendance = async () => {
    if (!attendanceClass) {
      toast.error('Please select a class');
      return;
    }
    if (!attendanceImage) {
      toast.error('Please capture a photo first');
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('class_name', attendanceClass);
      formData.append('face_image', attendanceImage);

      const response = await axios.post(`${API}/attendance/mark`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast.success(response.data.message);
      setAttendanceImage(null);
      fetchTodaysAttendance();
      fetchDashboardStats();
      stopCamera();
    } catch (error) {
      if (error.response?.status === 409) {
        toast.warning(error.response.data.message);
      } else if (error.response?.status === 404) {
        toast.error(error.response.data.message || 'Student not found');
      } else {
        toast.error('Error marking attendance');
      }
    }
    setLoading(false);
  };

  const filterStudentsByClass = (className) => {
    if (!className) return students;
    return students.filter(student => student.class_name === className);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="container mx-auto p-6">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Smart Attendance System
          </h1>
          <p className="text-gray-600">Automated attendance tracking with facial recognition</p>
        </header>

        {/* Dashboard Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Total Students</CardTitle>
              <Users className="h-5 w-5 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-gray-800">{dashboardStats.total_students}</div>
            </CardContent>
          </Card>

          <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Present Today</CardTitle>
              <UserCheck className="h-5 w-5 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{dashboardStats.present_today}</div>
            </CardContent>
          </Card>

          <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Attendance Rate</CardTitle>
              <CheckCircle className="h-5 w-5 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-600">{dashboardStats.attendance_rate}%</div>
            </CardContent>
          </Card>

          <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Active Classes</CardTitle>
              <GraduationCap className="h-5 w-5 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-orange-600">{dashboardStats.active_classes.length}</div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs defaultValue="attendance" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 bg-white shadow-sm">
            <TabsTrigger value="attendance" className="flex items-center gap-2">
              <Camera className="h-4 w-4" />
              Mark Attendance
            </TabsTrigger>
            <TabsTrigger value="students" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Manage Students
            </TabsTrigger>
            <TabsTrigger value="records" className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              View Records
            </TabsTrigger>
          </TabsList>

          {/* Mark Attendance Tab */}
          <TabsContent value="attendance">
            <Card className="bg-white shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Camera className="h-5 w-5 text-blue-600" />
                  Mark Attendance with Facial Recognition
                </CardTitle>
                <CardDescription>
                  Select a class and use the camera to mark attendance automatically
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="attendance-class">Select Class</Label>
                  <Select value={attendanceClass} onValueChange={setAttendanceClass}>
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a class" />
                    </SelectTrigger>
                    <SelectContent>
                      {classes.map(className => (
                        <SelectItem key={className} value={className}>
                          {className}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-4">
                  <div className="flex gap-4">
                    <Button 
                      onClick={startCamera} 
                      disabled={cameraActive}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      Start Camera
                    </Button>
                    <Button 
                      onClick={stopCamera} 
                      disabled={!cameraActive}
                      variant="outline"
                    >
                      Stop Camera
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                      <Label>Camera Feed</Label>
                      <div className="relative bg-gray-100 rounded-lg overflow-hidden">
                        <video
                          ref={videoRef}
                          autoPlay
                          className="w-full h-64 object-cover"
                          style={{ display: cameraActive ? 'block' : 'none' }}
                        />
                        {!cameraActive && (
                          <div className="w-full h-64 flex items-center justify-center bg-gray-200">
                            <p className="text-gray-500">Camera not active</p>
                          </div>
                        )}
                      </div>
                      <Button 
                        onClick={capturePhoto} 
                        disabled={!cameraActive}
                        className="w-full bg-green-600 hover:bg-green-700"
                      >
                        Capture Photo
                      </Button>
                    </div>

                    <div className="space-y-4">
                      <Label>Captured Image</Label>
                      <canvas
                        ref={canvasRef}
                        className="w-full h-64 border rounded-lg bg-gray-100"
                        style={{ display: attendanceImage ? 'block' : 'none' }}
                      />
                      {!attendanceImage && (
                        <div className="w-full h-64 flex items-center justify-center bg-gray-200 rounded-lg">
                          <p className="text-gray-500">No image captured</p>
                        </div>
                      )}
                      <Button 
                        onClick={markAttendance} 
                        disabled={!attendanceImage || !attendanceClass || loading}
                        className="w-full bg-purple-600 hover:bg-purple-700"
                      >
                        {loading ? 'Processing...' : 'Mark Attendance'}
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Students Tab */}
          <TabsContent value="students">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Add Student Form */}
              <Card className="bg-white shadow-lg">
                <CardHeader>
                  <CardTitle>Register New Student</CardTitle>
                  <CardDescription>Add a new student with face recognition data</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleStudentSubmit} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="student_name">Student Name</Label>
                      <Input
                        id="student_name"
                        value={newStudent.student_name}
                        onChange={(e) => setNewStudent({...newStudent, student_name: e.target.value})}
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="class_name">Class</Label>
                      <Input
                        id="class_name"
                        value={newStudent.class_name}
                        onChange={(e) => setNewStudent({...newStudent, class_name: e.target.value})}
                        placeholder="e.g., Grade 10A"
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="roll_no">Roll Number</Label>
                      <Input
                        id="roll_no"
                        type="number"
                        value={newStudent.roll_no}
                        onChange={(e) => setNewStudent({...newStudent, roll_no: e.target.value})}
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="father_name">Father's Name</Label>
                      <Input
                        id="father_name"
                        value={newStudent.father_name}
                        onChange={(e) => setNewStudent({...newStudent, father_name: e.target.value})}
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="face_image">Face Image</Label>
                      <Input
                        id="face_image"
                        type="file"
                        accept="image/*"
                        onChange={(e) => setSelectedImage(e.target.files[0])}
                        required
                      />
                    </div>

                    <Button type="submit" disabled={loading} className="w-full bg-blue-600 hover:bg-blue-700">
                      {loading ? 'Registering...' : 'Register Student'}
                    </Button>
                  </form>
                </CardContent>
              </Card>

              {/* Students List */}
              <Card className="bg-white shadow-lg">
                <CardHeader>
                  <CardTitle>Students Directory</CardTitle>
                  <CardDescription>
                    <div className="flex items-center gap-4">
                      <span>Total: {students.length} students</span>
                      <Select value={selectedClass} onValueChange={setSelectedClass}>
                        <SelectTrigger className="w-48">
                          <SelectValue placeholder="Filter by class" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">All Classes</SelectItem>
                          {classes.map(className => (
                            <SelectItem key={className} value={className}>
                              {className}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {filterStudentsByClass(selectedClass).map(student => (
                      <div key={student.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">{student.student_name}</div>
                          <div className="text-sm text-gray-600">
                            Class {student.class_name} • Roll {student.roll_no}
                          </div>
                          <div className="text-xs text-gray-500">Father: {student.father_name}</div>
                        </div>
                        <Badge variant="secondary">{student.class_name}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Records Tab */}
          <TabsContent value="records">
            <Card className="bg-white shadow-lg">
              <CardHeader>
                <CardTitle>Today's Attendance Records</CardTitle>
                <CardDescription>
                  Real-time attendance tracking for {new Date().toLocaleDateString()}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {attendanceRecords.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                      <p>No attendance records for today</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {attendanceRecords.map(record => (
                        <div key={record.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex items-center gap-4">
                            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                              <CheckCircle className="h-5 w-5 text-green-600" />
                            </div>
                            <div>
                              <div className="font-medium">{record.student_name}</div>
                              <div className="text-sm text-gray-600">
                                Class {record.class_name} • Roll {record.roll_no}
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge className="bg-green-100 text-green-800">Present</Badge>
                            <div className="text-sm text-gray-500 mt-1">{record.time}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;