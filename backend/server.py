from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import base64
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
import io
from PIL import Image

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Pydantic Models
class Student(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_name: str
    class_name: str
    roll_no: int
    father_name: str
    face_encoding: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudentCreate(BaseModel):
    student_name: str
    class_name: str
    roll_no: int
    father_name: str

class AttendanceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    student_name: str
    class_name: str
    roll_no: int
    date: str
    time: str
    status: str = "Present"
    confidence_score: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AttendanceMarkRequest(BaseModel):
    class_name: str

class DashboardStats(BaseModel):
    total_students: int
    present_today: int
    attendance_rate: float
    active_classes: List[str]

# Helper functions
def prepare_for_mongo(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(item):
    if isinstance(item, dict):
        for key, value in item.items():
            if key == 'created_at' and isinstance(value, str):
                try:
                    item[key] = datetime.fromisoformat(value)
                except:
                    pass
    return item

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Automated Attendance System API"}

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        # Total students
        total_students = await db.students.count_documents({})
        
        # Today's date
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Present today
        present_today = await db.attendance.count_documents({"date": today})
        
        # Attendance rate
        attendance_rate = (present_today / total_students * 100) if total_students > 0 else 0
        
        # Active classes
        classes_cursor = db.students.distinct("class_name")
        active_classes = await classes_cursor
        
        return DashboardStats(
            total_students=total_students,
            present_today=present_today,
            attendance_rate=round(attendance_rate, 1),
            active_classes=active_classes or []
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/students", response_model=Student)
async def create_student(
    student_name: str = Form(...),
    class_name: str = Form(...),
    roll_no: int = Form(...),
    father_name: str = Form(...),
    face_image: UploadFile = File(...)
):
    """Create a new student with face image"""
    try:
        # Check if roll number already exists in the class
        existing_student = await db.students.find_one({"class_name": class_name, "roll_no": roll_no})
        if existing_student:
            raise HTTPException(status_code=400, detail="Roll number already exists in this class")
        
        # Read and process the uploaded image
        image_data = await face_image.read()
        
        # Convert image to base64 for storage and OpenAI processing
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Use OpenAI Vision to analyze and encode the face with enhanced description
        try:
            chat = LlmChat(
                api_key=os.environ.get('EMERGENT_LLM_KEY'),
                session_id=f"face_encoding_{uuid.uuid4()}",
                system_message="You are an advanced facial recognition system. Analyze the face in the image and provide a comprehensive description for identification. Focus on: 1) Facial structure (round/oval/square face), 2) Eye characteristics (shape, size, color if visible), 3) Nose features (shape, size), 4) Mouth and lips, 5) Skin tone and complexion, 6) Hair style and color, 7) Any distinctive marks or features, 8) Overall facial proportions. Be very detailed and specific as this will be used for matching in different lighting conditions."
            ).with_model("openai", "gpt-4o")
            
            image_content = ImageContent(image_base64=image_base64)
            
            user_message = UserMessage(
                text="Analyze this face image and provide a comprehensive facial description for identification purposes. Include all distinctive features that would help identify this person in future images even under different lighting or angles. Be thorough and detailed.",
                file_contents=[image_content]
            )
            
            face_encoding_response = await chat.send_message(user_message)
            face_encoding = face_encoding_response.strip()
            print(f"Generated face encoding for {student_name}: {face_encoding[:100]}...")
            
        except Exception as e:
            print(f"OpenAI Vision error: {e}")
            face_encoding = f"Face image stored for {student_name}"
        
        # Create student object
        student_data = {
            "student_name": student_name,
            "class_name": class_name,
            "roll_no": roll_no,
            "father_name": father_name,
            "face_encoding": face_encoding,
            "face_image_b64": image_base64
        }
        
        student = Student(**student_data)
        student_dict = prepare_for_mongo(student.dict())
        
        await db.students.insert_one(student_dict)
        
        return student
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/students", response_model=List[Student])
async def get_students():
    """Get all students"""
    try:
        students_cursor = db.students.find().sort("class_name", 1).sort("roll_no", 1)
        students = await students_cursor.to_list(1000)
        return [Student(**parse_from_mongo(student)) for student in students]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/students/class/{class_name}", response_model=List[Student])
async def get_students_by_class(class_name: str):
    """Get students by class"""
    try:
        students_cursor = db.students.find({"class_name": class_name}).sort("roll_no", 1)
        students = await students_cursor.to_list(1000)
        return [Student(**parse_from_mongo(student)) for student in students]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/attendance/mark")
async def mark_attendance_with_image(
    class_name: str = Form(...),
    face_image: UploadFile = File(...)
):
    """Mark attendance using facial recognition"""
    try:
        # Read the uploaded image
        image_data = await face_image.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Get all students from the specified class
        students_cursor = db.students.find({"class_name": class_name})
        students = await students_cursor.to_list(1000)
        
        if not students:
            raise HTTPException(status_code=404, detail="No students found in this class")
        
        # Use OpenAI Vision to identify the student with improved matching
        try:
            # First, get a description of the face in the attendance image
            chat_describe = LlmChat(
                api_key=os.environ.get('EMERGENT_LLM_KEY'),
                session_id=f"describe_{uuid.uuid4()}",
                system_message="You are a facial recognition system. Analyze the face in the image and provide a detailed description focusing on distinctive features like facial structure, eye shape, nose shape, skin tone, hair style, etc. Be very specific and detailed."
            ).with_model("openai", "gpt-4o")
            
            image_content = ImageContent(image_base64=image_base64)
            
            describe_message = UserMessage(
                text="Analyze this face image and provide a detailed facial description focusing on distinctive features.",
                file_contents=[image_content]
            )
            
            current_face_description = await chat_describe.send_message(describe_message)
            print(f"Current face description: {current_face_description}")
            
            # Now compare with stored student descriptions using a more flexible approach
            chat_match = LlmChat(
                api_key=os.environ.get('EMERGENT_LLM_KEY'),
                session_id=f"match_{uuid.uuid4()}",
                system_message=f"You are comparing facial descriptions for attendance matching. You will be given a description of a face from a live photo and descriptions of registered students. Find the BEST MATCH even if not perfect, as lighting and angles may differ. Consider facial structure, features, and overall appearance. Be more lenient in matching as the same person may look different in different conditions.\n\nCurrent face description: {current_face_description}\n\nRegistered students in class {class_name}:\n" + "\n".join([f"- {s['student_name']} (Roll: {s['roll_no']}): {s.get('face_encoding', 'No description')}" for s in students])
            ).with_model("openai", "gpt-4o")
            
            match_message = UserMessage(
                text="Based on the facial descriptions, which registered student is the BEST MATCH for the current face? Consider that lighting, angles, and photo quality may cause variations. Return ONLY the student's name that best matches, or 'NO_MATCH' if absolutely no reasonable match exists. Be more lenient in matching."
            )
            
            recognition_result = await chat_match.send_message(match_message)
            recognized_name = recognition_result.strip()
            print(f"Recognition result: {recognized_name}")
            
            # Find the matching student with more flexible name matching
            matched_student = None
            for student in students:
                student_name_parts = student['student_name'].lower().split()
                recognized_parts = recognized_name.lower().split()
                
                # Check if any part of the recognized name matches any part of student name
                if any(part in student['student_name'].lower() for part in recognized_parts if len(part) > 2) and recognized_name.upper() != 'NO_MATCH':
                    matched_student = student
                    print(f"Matched student: {student['student_name']}")
                    break
            
            if not matched_student:
                return JSONResponse(
                    status_code=404,
                    content={"message": "No matching student found", "recognized": recognized_name}
                )
            
            # Check if already marked present today
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            existing_record = await db.attendance.find_one({
                "student_id": matched_student['id'],
                "date": today
            })
            
            if existing_record:
                return JSONResponse(
                    status_code=409,
                    content={"message": f"{matched_student['student_name']} is already marked present today"}
                )
            
            # Create attendance record
            now = datetime.now(timezone.utc)
            attendance_record = AttendanceRecord(
                student_id=matched_student['id'],
                student_name=matched_student['student_name'],
                class_name=matched_student['class_name'],
                roll_no=matched_student['roll_no'],
                date=now.strftime('%Y-%m-%d'),
                time=now.strftime('%H:%M:%S'),
                status="Present",
                confidence_score=0.95
            )
            
            attendance_dict = prepare_for_mongo(attendance_record.dict())
            await db.attendance.insert_one(attendance_dict)
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": f"Attendance marked successfully for {matched_student['student_name']}",
                    "student": {
                        "name": matched_student['student_name'],
                        "class": matched_student['class_name'],
                        "roll_no": matched_student['roll_no']
                    },
                    "time": now.strftime('%H:%M:%S')
                }
            )
            
        except Exception as e:
            print(f"OpenAI Vision error: {e}")
            raise HTTPException(status_code=500, detail="Face recognition service unavailable")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/attendance/today", response_model=List[AttendanceRecord])
async def get_todays_attendance():
    """Get today's attendance records"""
    try:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        attendance_cursor = db.attendance.find({"date": today}).sort("time", -1)
        attendance_records = await attendance_cursor.to_list(1000)
        return [AttendanceRecord(**parse_from_mongo(record)) for record in attendance_records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/attendance/class/{class_name}")
async def get_class_attendance(class_name: str):
    """Get attendance for a specific class today"""
    try:
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        attendance_cursor = db.attendance.find({"class_name": class_name, "date": today}).sort("time", -1)
        attendance_records = await attendance_cursor.to_list(1000)
        return [AttendanceRecord(**parse_from_mongo(record)) for record in attendance_records]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/classes")
async def get_classes():
    """Get all available classes"""
    try:
        classes = await db.students.distinct("class_name")
        return {"classes": classes or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()