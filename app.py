from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import jwt
import hashlib
import secrets
import os
from functools import wraps


# Use environment variables for sensitive info
app = Flask(__name__)
from dotenv import load_dotenv
load_dotenv()

# Restrict CORS for production
if os.environ.get('FLASK_ENV') == 'production':
    CORS(app, origins=[os.environ.get('FRONTEND_ORIGIN', 'http://localhost:8000')])
else:
    CORS(app)

# Configuration
# Change this to a strong secret key for production

# Use environment variables for secret key and Mongo URI
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'shoeb@123_secure_key_production')
MONGO_URI = os.environ.get('MONGO_URI', "mongodb+srv://Shoeb:shoeb5550@cluster0.hkjhmtc.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DATABASE_NAME = os.environ.get('DATABASE_NAME', "Institute")

# Global variables for database
client = None
db = None
users_collection = None
students_collection = None
courses_collection = None
payments_collection = None

# Initialize MongoDB connection
def init_mongodb():
    global client, db, users_collection, students_collection, courses_collection, payments_collection
    
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Test the connection
        client.admin.command('ping')
        db = client[DATABASE_NAME]
        
        # Initialize collections
        users_collection = db.users
        students_collection = db.students
        courses_collection = db.courses
        payments_collection = db.payments
        
        print("✅ Connected to MongoDB successfully!")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("⚠️  Running in offline mode - data will not persist")
        return False

# Predefined users - You can easily add more here
PREDEFINED_USERS = {
    "Shoeb": {
        "password": "Shoeb5550",
        "email": "shoeb@institute.com",
        "role": "admin"
    },
    "admin": {
        "password": "admin123",
        "email": "admin@institute.com", 
        "role": "admin"
    }
}

# In-memory storage for offline mode
offline_data = {
    'students': [],
    'courses': [
        {"_id": "1", "name": "O LEVEL", "duration": "12 months", "fee": 18200, "description": "DOEACC O Level Computer Course"},
        {"_id": "2", "name": "DIT", "duration": "12 months", "fee": 16000, "description": "Diploma in Information Technology"},
        {"_id": "3", "name": "TALLY PRIME WITH EXCEL", "duration": "3 months", "fee": 7200, "description": "Tally Prime with Advanced Excel"},
        {"_id": "4", "name": "CCC", "duration": "3 months", "fee": 3600, "description": "Course on Computer Concepts (NIELIT)"},
        {"_id": "5", "name": "ADCA", "duration": "12 months", "fee": 14000, "description": "Advanced Diploma in Computer Applications"},
        {"_id": "6", "name": "DCA", "duration": "6 months", "fee": 7200, "description": "Diploma in Computer Applications"},
        {"_id": "7", "name": "ADVANCE EXCEL", "duration": "2 months", "fee": 4000, "description": "Advanced Microsoft Excel"},
        {"_id": "8", "name": "PYTHON", "duration": "3 months", "fee": 4500, "description": "Python Programming Course"},
        {"_id": "9", "name": "IOT", "duration": "4 months", "fee": 4500, "description": "Internet of Things Fundamentals"},
        {"_id": "10", "name": "DTP", "duration": "3 months", "fee": 4500, "description": "Desktop Publishing"},
        {"_id": "11", "name": "C++", "duration": "2 months", "fee": 3500, "description": "C++ Programming"},
        {"_id": "12", "name": "C LANGUAGE", "duration": "2 months", "fee": 4500, "description": "C Programming Language"},
        {"_id": "13", "name": "HINDI/ENGLISH TYPING", "duration": "2 months", "fee": 3200, "description": "Hindi/English Typing Course"}
    ],
    'payments': [],
    'users': []
}

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

def generate_token(user_data):
    """Generate JWT token"""
    payload = {
        'user_id': str(user_data.get('_id', user_data['username'])),
        'username': user_data['username'],
        'role': user_data['role'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def token_required(f):
    """Decorator to require valid token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

def init_default_data():
    """Initialize default users and courses"""
    if db is None:
        print("⚠️  Database not available - using offline mode")
        return
    
    try:
        # Initialize users
        for username, user_data in PREDEFINED_USERS.items():
            existing_user = users_collection.find_one({"username": username})
            if not existing_user:
                user_doc = {
                    "username": username,
                    "email": user_data["email"],
                    "password": hash_password(user_data["password"]),
                    "role": user_data["role"],
                    "created_at": datetime.utcnow()
                }
                users_collection.insert_one(user_doc)
                print(f"✅ Created user: {username}")
        
        # Initialize default courses
        default_courses = [
            {"name": "O LEVEL", "duration": "12 months", "fee": 18200, "description": "DOEACC O Level Computer Course"},
            {"name": "DIT", "duration": "12 months", "fee": 16000, "description": "Diploma in Information Technology"},
            {"name": "TALLY PRIME WITH EXCEL", "duration": "3 months", "fee": 7200, "description": "Tally Prime with Advanced Excel"},
            {"name": "CCC", "duration": "3 months", "fee": 3600, "description": "Course on Computer Concepts (NIELIT)"},
            {"name": "ADCA", "duration": "12 months", "fee": 14000, "description": "Advanced Diploma in Computer Applications"},
            {"name": "DCA", "duration": "6 months", "fee": 7200, "description": "Diploma in Computer Applications"},
            {"name": "ADVANCE EXCEL", "duration": "2 months", "fee": 4000, "description": "Advanced Microsoft Excel"},
            {"name": "PYTHON", "duration": "3 months", "fee": 4500, "description": "Python Programming Course"},
            {"name": "IOT", "duration": "4 months", "fee": 4500, "description": "Internet of Things Fundamentals"},
            {"name": "DTP", "duration": "3 months", "fee": 4500, "description": "Desktop Publishing"},
            {"name": "C++", "duration": "2 months", "fee": 3500, "description": "C++ Programming"},
            {"name": "C LANGUAGE", "duration": "2 months", "fee": 4500, "description": "C Programming Language"},
            {"name": "HINDI/ENGLISH TYPING", "duration": "2 months", "fee": 3200, "description": "Hindi/English Typing Course"}
        ]
        
        for course in default_courses:
            existing_course = courses_collection.find_one({"name": course["name"]})
            if not existing_course:
                course["created_at"] = datetime.utcnow()
                courses_collection.insert_one(course)
                print(f"✅ Created course: {course['name']}")
                
    except Exception as e:
        print(f"❌ Error initializing data: {e}")

# Routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400
        
        # Check predefined users first
        if username in PREDEFINED_USERS:
            if PREDEFINED_USERS[username]['password'] == password:
                user_data = {
                    'username': username,
                    'email': PREDEFINED_USERS[username]['email'],
                    'role': PREDEFINED_USERS[username]['role']
                }
                token = generate_token(user_data)
                return jsonify({
                    'success': True,
                    'token': token,
                    'user': user_data
                })
        
        # Check database users if available
        if db is not None and users_collection is not None:
            try:
                user = users_collection.find_one({"username": username})
                print("DEBUG: User found in database:", user)  # Debug print
                if user and verify_password(password, user['password']):
                    user_data = {
                        '_id': user['_id'],
                        'username': user['username'],
                        'email': user['email'],
                        'role': user['role']
                    }
                    token = generate_token(user_data)
                    return jsonify({
                        'success': True,
                        'token': token,
                        'user': {
                            'username': user['username'],
                            'email': user['email'],
                            'role': user['role']
                        }
                    })
            except Exception as e:
                print(f"Database user check error: {e}")
        else:
            print("DEBUG: Database not available, skipping database check")  # Debug print
        
        # Check offline users if available
        print("DEBUG: Checking offline users, count:", len(offline_data['users']))  # Debug print
        for user in offline_data['users']:
            print("DEBUG: Checking offline user:", user)  # Debug print
            if user['username'] == username and verify_password(password, user['password']):
                user_data = {
                    'username': user['username'],
                    'email': user.get('email', ''),
                    'role': user['role']
                }
                token = generate_token(user_data)
                return jsonify({
                    'success': True,
                    'token': token,
                    'user': user_data
                })
        
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500

@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    return jsonify({
        'success': True,
        'user': {
            'username': current_user['username'],
            'role': current_user['role']
        }
    })

@app.route('/api/students', methods=['GET'])
@token_required
def get_students(current_user):
    try:
        # Pagination params
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
        if db is not None and students_collection is not None:
            total = students_collection.count_documents({})
            students = list(students_collection.find().skip((page-1)*page_size).limit(page_size))
            for student in students:
                student['_id'] = str(student['_id'])
            return jsonify({'success': True, 'data': students, 'total': total, 'page': page, 'page_size': page_size})
        else:
            # Return offline data with pagination
            total = len(offline_data['students'])
            start = (page-1)*page_size
            end = start+page_size
            students = offline_data['students'][start:end]
            return jsonify({'success': True, 'data': students, 'total': total, 'page': page, 'page_size': page_size})
    except Exception as e:
        print(f"Error getting students: {e}")
        return jsonify({'success': True, 'data': offline_data['students']})

@app.route('/api/students', methods=['POST'])
@token_required
def add_student(current_user):
    try:
        data = request.get_json()

        # Find course fee
        course_fee = 50000  # default
        if db is not None and courses_collection is not None:
            course = courses_collection.find_one({"name": data['course']})
            if course:
                course_fee = course['fee']
        else:
            # Check offline courses
            for course in offline_data['courses']:
                if course['name'] == data['course']:
                    course_fee = course['fee']
                    break

        student_data = {
            'name': data['name'],
            'father': data.get('father', ''),
            'dob': data.get('dob', ''),
            'phone': data.get('phone', ''),
            'course': data['course'],
            'branch': data.get('branch', ''),
            'total_fee': float(data.get('total_fee', course_fee)),
            'discount': float(data.get('discount', 0)),
            'paid_amount': 0,
            'status': 'Active',
            'enrollment_date': data.get('enrollment_date', datetime.utcnow().isoformat()),
            'created_at': datetime.utcnow()
        }

        if db is not None and students_collection is not None:
            result = students_collection.insert_one(student_data)
            student_data['_id'] = str(result.inserted_id)
        else:
            # Add to offline data
            student_data['_id'] = str(len(offline_data['students']) + 1)
            offline_data['students'].append(student_data)

        return jsonify({'success': True, 'data': student_data})

    except Exception as e:
        print(f"Error adding student: {e}")
        return jsonify({'success': False, 'message': 'Error adding student'}), 500

@app.route('/api/students/<student_id>', methods=['DELETE'])
@token_required
def delete_student(current_user, student_id):
    try:
        if db is not None and students_collection is not None:
            result = students_collection.delete_one({'_id': ObjectId(student_id)})
            if result.deleted_count == 1:
                return jsonify({'success': True, 'message': 'Student deleted successfully'})
            else:
                return jsonify({'success': False, 'message': 'Student not found'}), 404
        else:
            # Offline mode
            initial_count = len(offline_data['students'])
            offline_data['students'] = [s for s in offline_data['students'] if s['_id'] != student_id]
            if len(offline_data['students']) < initial_count:
                return jsonify({'success': True, 'message': 'Student deleted successfully'})
            else:
                return jsonify({'success': False, 'message': 'Student not found'}), 404
    except Exception as e:
        print(f"Error deleting student: {e}")
        return jsonify({'success': False, 'message': 'Error deleting student'}), 500

@app.route('/api/courses', methods=['GET'])
@token_required
def get_courses(current_user):
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
        if db is not None and courses_collection is not None:
            total = courses_collection.count_documents({})
            courses = list(courses_collection.find().skip((page-1)*page_size).limit(page_size))
            for course in courses:
                course['_id'] = str(course['_id'])
            return jsonify({'success': True, 'data': courses, 'total': total, 'page': page, 'page_size': page_size})
        else:
            total = len(offline_data['courses'])
            start = (page-1)*page_size
            end = start+page_size
            courses = offline_data['courses'][start:end]
            return jsonify({'success': True, 'data': courses, 'total': total, 'page': page, 'page_size': page_size})
    except Exception as e:
        print(f"Error getting courses: {e}")
        return jsonify({'success': True, 'data': offline_data['courses']})

@app.route('/api/courses', methods=['POST'])
@token_required
def add_course(current_user):
    try:
        data = request.get_json()
        
        course_data = {
            'name': data['name'],
            'duration': data['duration'],
            'fee': float(data['fee']),
            'description': data.get('description', ''),
            'created_at': datetime.utcnow()
        }
        
        if db is not None and courses_collection is not None:
            result = courses_collection.insert_one(course_data)
            course_data['_id'] = str(result.inserted_id)
        else:
            # Add to offline data
            course_data['_id'] = str(len(offline_data['courses']) + 1)
            offline_data['courses'].append(course_data)
        
        return jsonify({'success': True, 'data': course_data})
        
    except Exception as e:
        print(f"Error adding course: {e}")
        return jsonify({'success': False, 'message': 'Error adding course'}), 500

@app.route('/api/payments', methods=['GET'])
@token_required
def get_payments(current_user):
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
        if db is not None and payments_collection is not None:
            total = payments_collection.count_documents({})
            payments = list(payments_collection.find().sort('payment_date', -1).skip((page-1)*page_size).limit(page_size))
            for payment in payments:
                payment['_id'] = str(payment['_id'])
                if 'payment_date' in payment and hasattr(payment['payment_date'], 'isoformat'):
                    payment['payment_date'] = payment['payment_date'].isoformat()
            return jsonify({'success': True, 'data': payments, 'total': total, 'page': page, 'page_size': page_size})
        else:
            total = len(offline_data['payments'])
            start = (page-1)*page_size
            end = start+page_size
            payments = offline_data['payments'][start:end]
            return jsonify({'success': True, 'data': payments, 'total': total, 'page': page, 'page_size': page_size})
    except Exception as e:
        print(f"Error getting payments: {e}")
        return jsonify({'success': True, 'data': offline_data['payments']})

@app.route('/api/payments', methods=['POST'])
@token_required
def add_payment(current_user):
    try:
        data = request.get_json()
        
        # Find student
        student = None
        if db is not None and students_collection is not None:
            student = students_collection.find_one({"_id": ObjectId(data['student_id'])})
        else:
            # Find in offline data
            for s in offline_data['students']:
                if s['_id'] == data['student_id']:
                    student = s
                    break
        
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'}), 400
        
        # Generate receipt number
        receipt_number = f"RCP-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        
        payment_data = {
            'student_id': data['student_id'],
            'student_name': student['name'],
            'amount': float(data['amount']),
            'payment_method': data['payment_method'],
            'fee_type': data.get('fee_type', ''),
            'notes': data.get('notes', ''),
            'receipt_number': receipt_number,
            'payment_date': datetime.utcnow().isoformat(),
            'created_by': current_user['username']
        }
        
        if db is not None and payments_collection is not None:
            # Insert payment
            payment_data_db = payment_data.copy()
            payment_data_db['payment_date'] = datetime.utcnow()
            result = payments_collection.insert_one(payment_data_db)
            payment_data['_id'] = str(result.inserted_id)
            
            # Update student paid amount
            new_paid_amount = student.get('paid_amount', 0) + float(data['amount'])
            students_collection.update_one(
                {"_id": ObjectId(data['student_id'])},
                {"$set": {"paid_amount": new_paid_amount}}
            )
        else:
            # Add to offline data
            payment_data['_id'] = str(len(offline_data['payments']) + 1)
            offline_data['payments'].append(payment_data)
            
            # Update student in offline data
            for s in offline_data['students']:
                if s['_id'] == data['student_id']:
                    s['paid_amount'] = s.get('paid_amount', 0) + float(data['amount'])
                    break
        
        return jsonify({'success': True, 'data': payment_data})
        
    except Exception as e:
        print(f"Error adding payment: {e}")
        return jsonify({'success': False, 'message': 'Error processing payment'}), 500

@app.route('/api/users', methods=['GET'])
@token_required
def get_users(current_user):
    try:
        if current_user['role'] != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        if db is not None and users_collection is not None:
            users = list(users_collection.find({}, {'password': 0}))  # Exclude password
            for user in users:
                user['_id'] = str(user['_id'])
                # Convert datetime to string
                if 'created_at' in user and hasattr(user['created_at'], 'isoformat'):
                    user['created_at'] = user['created_at'].isoformat()
            return jsonify({'success': True, 'data': users})
        else:
            # Return offline data
            return jsonify({'success': True, 'data': offline_data['users']})
            
    except Exception as e:
        print(f"Error getting users: {e}")
        return jsonify({'success': True, 'data': offline_data['users']})

@app.route('/api/users', methods=['POST'])
@token_required
def add_user(current_user):
    try:
        if current_user['role'] != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        data = request.get_json()
        print("DEBUG: User data received from frontend:", data)  # Debug print
        
        # Check if username already exists
        username_exists = False
        if db is not None and users_collection is not None:
            if users_collection.find_one({"username": data['username']}):
                username_exists = True
        else:
            # Check offline data
            for user in offline_data['users']:
                if user['username'] == data['username']:
                    username_exists = True
                    break
        
        if username_exists:
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        user_data = {
            'username': data['username'],
            'email': data.get('email', ''),
            'password': hash_password(data['password']),
            'role': data['role'],
            'created_at': datetime.utcnow().isoformat()
        }
        print("DEBUG: User data to insert:", user_data)  # Debug print
        
        if db is not None and users_collection is not None:
            user_data_db = user_data.copy()
            user_data_db['created_at'] = datetime.utcnow()
            result = users_collection.insert_one(user_data_db)
            user_data['_id'] = str(result.inserted_id)
            print("DEBUG: User inserted into MongoDB with ID:", result.inserted_id)  # Debug print
        else:
            # Add to offline data
            user_data['_id'] = str(len(offline_data['users']) + 1)
            offline_data['users'].append(user_data)
            print("DEBUG: User added to offline data")  # Debug print
        
        # Create response data without password
        response_data = user_data.copy()
        del response_data['password']  # Don't return password in response
        return jsonify({'success': True, 'data': response_data})
        
    except Exception as e:
        print(f"Error adding user: {e}")
        return jsonify({'success': False, 'message': 'Error adding user'}), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    if current_user['role'] != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    try:
        data = request.get_json()
        update_fields = {}
        if 'username' in data:
            update_fields['username'] = data['username']
        if 'password' in data and data['password']:
            update_fields['password'] = hash_password(data['password'])
        if not update_fields:
            return jsonify({'success': False, 'message': 'No fields to update'}), 400
        if db is not None and users_collection is not None:
            result = users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': update_fields})
            if result.matched_count == 1:
                return jsonify({'success': True, 'message': 'User updated successfully'})
            else:
                return jsonify({'success': False, 'message': 'User not found'}), 404
        else:
            # Offline mode
            for user in offline_data['users']:
                if user['_id'] == user_id:
                    user.update(update_fields)
                    return jsonify({'success': True, 'message': 'User updated successfully'})
            return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        print(f"Error updating user: {e}")
        return jsonify({'success': False, 'message': 'Error updating user'}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    if current_user['role'] != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    try:
        if db is not None and users_collection is not None:
            result = users_collection.delete_one({'_id': ObjectId(user_id)})
            if result.deleted_count == 1:
                return jsonify({'success': True, 'message': 'User deleted successfully'})
            else:
                return jsonify({'success': False, 'message': 'User not found'}), 404
        else:
            # Offline mode
            initial_count = len(offline_data['users'])
            offline_data['users'] = [u for u in offline_data['users'] if u['_id'] != user_id]
            if len(offline_data['users']) < initial_count:
                return jsonify({'success': True, 'message': 'User deleted successfully'})
            else:
                return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        print(f"Error deleting user: {e}")
        return jsonify({'success': False, 'message': 'Error deleting user'}), 500

@app.route('/api/students/<student_id>/status', methods=['PUT'])
@token_required
def update_student_status(current_user, student_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'}), 400
        
        if db is not None and students_collection is not None:
            result = students_collection.update_one(
                {'_id': ObjectId(student_id)},
                {'$set': {'status': new_status}}
            )
            if result.matched_count == 1:
                return jsonify({'success': True, 'message': 'Student status updated successfully'})
            else:
                return jsonify({'success': False, 'message': 'Student not found'}), 404
        else:
            # Offline mode
            for student in offline_data['students']:
                if student['_id'] == student_id:
                    student['status'] = new_status
                    return jsonify({'success': True, 'message': 'Student status updated successfully'})
            return jsonify({'success': False, 'message': 'Student not found'}), 404
    except Exception as e:
        print(f"Error updating student status: {e}")
        return jsonify({'success': False, 'message': 'Error updating student status'}), 500

@app.route('/api/system/status', methods=['GET'])
def system_status():
    return jsonify({
        'success': True,
        'setup_required': False,
        'database_connected': db is not None
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Institute Management System API',
        'status': 'running',
        'database_connected': db is not None,
        'endpoints': [
            '/api/auth/login',
            '/api/auth/verify',
            '/api/students',
            '/api/courses',
            '/api/payments',
            '/api/users'
        ]
    })

if __name__ == '__main__':
    print("🚀 Starting Institute Management System...")
    print("📊 Initializing database...")
    
    # Initialize MongoDB
    mongodb_connected = init_mongodb()
    
    if mongodb_connected:
        init_default_data()
        print("✅ Database initialized successfully!")
    else:
        print("⚠️  Running in offline mode - data will not persist between restarts")
    
    print("\n👥 Available Users:")
    for username, user_data in PREDEFINED_USERS.items():
        print(f"   • {username} / {user_data['password']} ({user_data['role']})")
    
    print(f"\n🌐 Server starting on http://localhost:5000")
    print("📱 Frontend should be on http://localhost:8000")
    print("\n" + "="*50)
    
    # For production, use:
    # app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
    # For development:
    app.run(debug=True, host='0.0.0.0', port=5000)

