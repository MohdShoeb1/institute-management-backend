from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from config import config
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from dateutil import parser
import bcrypt
import jwt
import secrets
import os
from functools import wraps


# Use environment variables for sensitive info
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[FLASK_ENV])
app.config['SQLALCHEMY_DATABASE_URI'] = config[FLASK_ENV].SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config[FLASK_ENV].SQLALCHEMY_TRACK_MODIFICATIONS
 
# Initialize SQLAlchemy
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    father = db.Column(db.String(120), nullable=True)
    dob = db.Column(db.Date, nullable=True) # Storing as string for simplicity, consider Date type for more complex queries
    phone = db.Column(db.String(20), nullable=True)
    course = db.Column(db.String(120), nullable=False)
    branch = db.Column(db.String(120), nullable=True)
    total_fee = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    paid_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default='Active')
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Student {self.name}>'

    def get_calculated_status(self):
        """Calculates the student's status based on payment and course duration."""
        # Dropped status is final and overrides other calculations
        if self.status == "Dropped":
            return "Dropped"

        # If fully paid, they are Completed
        net_fee = self.total_fee - (self.discount or 0)
        if (self.paid_amount or 0) >= net_fee:
            return "Completed"

        # Check for inactivity based on course duration from associated course
        course = Course.query.filter_by(name=self.course).first()
        if course and course.duration and self.enrollment_date:
            duration_in_months_str = ''.join(filter(str.isdigit, course.duration))
            if duration_in_months_str:
                duration_in_months = int(duration_in_months_str)
                end_date = self.enrollment_date + timedelta(days=duration_in_months * 30) # Approximation
                if datetime.utcnow() > end_date:
                    return "Inactive"
        
        return "Active"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'father': self.father,
            'dob': self.dob.isoformat() if self.dob else None,
            'phone': self.phone,
            'course': self.course,
            'branch': self.branch,
            'total_fee': self.total_fee,
            'discount': self.discount,
            'paid_amount': self.paid_amount,
            'status': self.status, # Keep existing status for direct update/reference
            'calculated_status': self.get_calculated_status(), # Add calculated status
            'enrollment_date': self.enrollment_date.isoformat() if self.enrollment_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    fee = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Course {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'duration': self.duration,
            'fee': self.fee,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    student_name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    fee_type = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    receipt_number = db.Column(db.String(100), unique=True, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80), nullable=True)

    student = db.relationship('Student', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f'<Payment {self.receipt_number}>'

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student_name,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'fee_type': self.fee_type,
            'notes': self.notes,
            'receipt_number': self.receipt_number,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'created_by': self.created_by
        }

# CORS Configuration
cors_config = {
    "supports_credentials": False,
    "allow_headers": ["Content-Type", "Authorization"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "expose_headers": ["Content-Type"],
    "max_age": 600
}
# Restrict CORS for production
if FLASK_ENV == 'production':
    cors_config["origins"] = [os.environ.get('FRONTEND_ORIGIN', 'http://localhost:8000')]
CORS(app, **cors_config)

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_token(user_data):
    """Generate JWT token"""
    payload = {
        'user_id': user_data['id'],
        'username': user_data['username'],
        'role': user_data['role'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

def token_required(f):
    """Decorator to require valid token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == 'OPTIONS':
            return ('', 204)

        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'success': False, 'message': 'Token is missing'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = {'id': data['user_id'], 'username': data['username'], 'role': data['role']}
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': 'Token is invalid'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

def init_default_data():
    """Initialize default users and courses"""
    try:
        # Ensure tables are created
        db.create_all()

        # Create a default admin user if no users exist
        if not User.query.first():
            default_admin_username = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
            default_admin_password = secrets.token_urlsafe(16) # Generate a strong, random password
            hashed_password = hash_password(default_admin_password)
            
            admin_user = User(
                username=default_admin_username,
                email=f"{default_admin_username}@institute.com",
                password=hashed_password,
                role="admin"
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f"✅ Created default admin user: Username='{default_admin_username}', Password='{default_admin_password}'")
            print("⚠️ IMPORTANT: Please change this password immediately after your first login via the frontend.")

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

        for course_data in default_courses:
            if not Course.query.filter_by(name=course_data['name']).first():
                course = Course(
                    name=course_data['name'],
                    duration=course_data['duration'],
                    fee=course_data['fee'],
                    description=course_data['description']
                )
                db.session.add(course)
                print(f"✅ Created course: {course.name}")

        db.session.commit()
        print("✅ Default data initialized successfully!")
    except Exception as e:
        db.session.rollback()
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
        
        user = User.query.filter_by(username=username).first()
        if user and verify_password(password, user.password):
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
            token = generate_token(user_data)
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                }
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
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
        students_pagination = Student.query.paginate(page=page, per_page=page_size, error_out=False)
        students_data = [student.to_dict() for student in students_pagination.items]
        return jsonify({'success': True, 'data': students_data, 'total': students_pagination.total, 'page': students_pagination.page, 'page_size': page_size})
    except Exception as e:
        print(f"Error getting students: {e}")
        return jsonify({'success': False, 'message': 'Error getting students'}), 500

@app.route('/api/students', methods=['POST'])
@token_required
def add_student(current_user):
    try:
        data = request.get_json()

        # Find course fee
        course_fee = None
        course_obj = Course.query.filter_by(name=data['course']).first()
        if course_obj:
            course_fee = course_obj.fee

        if course_fee is None:
            return jsonify({'success': False, 'message': f"Course '{data['course']}' not found. Cannot determine fee."}), 400

        student_data = {
            'name': data['name'],
            'father': data.get('father', ''),
            'dob': parser.parse(data.get('dob')).date() if data.get('dob') else None, # Parse string to date
            'phone': data.get('phone', ''),
            'course': data['course'],
            'branch': data.get('branch', ''),
            'total_fee': float(data.get('total_fee', course_fee)),
            'discount': float(data.get('discount', 0)),
            'paid_amount': 0,
            'status': 'Active',
            'enrollment_date': parser.parse(data.get('enrollment_date')) if data.get('enrollment_date') else datetime.utcnow(),
            'created_at': datetime.utcnow()
        }

        student = Student(**student_data)
        db.session.add(student)
        db.session.commit()

        return jsonify({'success': True, 'data': student.to_dict()})

    except Exception as e:
        db.session.rollback()
        print(f"Error adding student: {e}")
        return jsonify({'success': False, 'message': 'Error adding student'}), 500

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
@token_required
def delete_student(current_user, student_id):
    try:
        student_to_delete = db.session.get(Student, student_id)
        if not student_to_delete:
            return jsonify({'success': False, 'message': 'Student not found'}), 404

        # Delete associated payments first to maintain data integrity
        Payment.query.filter_by(student_id=student_id).delete()

        db.session.delete(student_to_delete)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Student deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting student: {e}")
        return jsonify({'success': False, 'message': 'Error deleting student'}), 500

@app.route('/api/courses', methods=['GET'])
@token_required
def get_courses(current_user):
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
        courses_pagination = Course.query.paginate(page=page, per_page=page_size, error_out=False)
        courses_data = [course.to_dict() for course in courses_pagination.items]
        return jsonify({'success': True, 'data': courses_data, 'total': courses_pagination.total, 'page': courses_pagination.page, 'page_size': page_size})
    except Exception as e:
        print(f"Error getting courses: {e}")
        return jsonify({'success': False, 'message': 'Error getting courses'}), 500

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
        
        course = Course(**course_data)
        db.session.add(course)
        db.session.commit()
        
        return jsonify({'success': True, 'data': course.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding course: {e}")
        return jsonify({'success': False, 'message': 'Error adding course'}), 500

@app.route('/api/payments', methods=['GET'])
@token_required
def get_payments(current_user):
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 25))
        payments_pagination = Payment.query.order_by(Payment.payment_date.desc()).paginate(page=page, per_page=page_size, error_out=False)
        payments_data = [payment.to_dict() for payment in payments_pagination.items]
        return jsonify({'success': True, 'data': payments_data, 'total': payments_pagination.total, 'page': payments_pagination.page, 'page_size': page_size})
    except Exception as e:
        print(f"Error getting payments: {e}")
        return jsonify({'success': False, 'message': 'Error getting payments'}), 500

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
@cross_origin()
@token_required
def get_stats(current_user):
    try:
        # Calculate stats dynamically
        total_students = db.session.query(db.func.count(Student.id)).scalar()
        total_revenue = db.session.query(db.func.sum(Payment.amount)).scalar() or 0.0
        
        # Calculate total pending fees
        total_fees_due = db.session.query(db.func.sum(Student.total_fee - Student.discount)).scalar() or 0.0
        total_pending = total_fees_due - total_revenue

        total_courses = Course.query.count()

        return jsonify({
            "success": True,
            "data": {
                'total_students': total_students, 'total_revenue': total_revenue, 'total_pending': total_pending, 'total_courses': total_courses
            }
        })
    except Exception as e:
        print(f"Error in get_stats: {e}")
        return jsonify({"success": False, "message": "Error fetching stats"}), 500


@app.route('/api/payments', methods=['POST'])
@token_required
def add_payment(current_user):
    try:
        data = request.get_json()
        
        # Find student
        student = db.session.get(Student, data['student_id'])
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'}), 400

        # Generate receipt number
        receipt_number = f"RCP-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        
        payment_data = {
            'student_id': data['student_id'],
            'student_name': student.name,
            'amount': float(data['amount']),
            'payment_method': data['payment_method'],
            'fee_type': data.get('fee_type', ''),
            'notes': data.get('notes', ''),
            'receipt_number': receipt_number,
            'payment_date': datetime.utcnow(),
            'created_by': current_user['username']
        }
        
        payment = Payment(**payment_data)
        db.session.add(payment)

        # Update student paid amount
        student.paid_amount += float(data['amount'])

        db.session.commit()
        
        return jsonify({'success': True, 'data': payment.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding payment: {e}")
        return jsonify({'success': False, 'message': 'Error processing payment'}), 500

@app.route('/api/users', methods=['GET'])
@token_required
def get_users(current_user):
    try:
        if current_user['role'] != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        users = User.query.all()
        return jsonify({'success': True, 'data': [user.to_dict() for user in users]})
            
    except Exception as e:
        print(f"Error getting users: {e}")
        return jsonify({'success': False, 'message': 'Error getting users'}), 500

@app.route('/api/users', methods=['POST'])
@token_required
def add_user(current_user):
    try:
        if current_user['role'] != 'admin':
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        data = request.get_json()
        print("DEBUG: User data received from frontend:", data)  # Debug print
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        user_data = {
            'username': data['username'],
            'email': data.get('email', ''),
            'password': hash_password(data['password']),
            'role': data['role'],
            'created_at': datetime.utcnow()
        }
        print("DEBUG: User data to insert:", user_data)  # Debug print
        
        user = User(**user_data)
        db.session.add(user)
        db.session.commit()
        print("DEBUG: User added to database")  # Debug print
        
        # Create response data without password
        return jsonify({'success': True, 'data': user.to_dict()})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding user: {e}")
        return jsonify({'success': False, 'message': 'Error adding user'}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
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
            update_fields['password'] = hash_password(data['password']) # bcrypt returns a string
        if not update_fields:
            return jsonify({'success': False, 'message': 'No fields to update'}), 400

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        for key, value in update_fields.items():
            setattr(user, key, value)

        db.session.commit()
        return jsonify({'success': True, 'message': 'User updated successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Error updating user: {e}")
        return jsonify({'success': False, 'message': 'Error updating user'}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    if current_user['role'] != 'admin':
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    try:
        user_to_delete = db.session.get(User, user_id)
        if not user_to_delete:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        db.session.delete(user_to_delete)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user: {e}")
        return jsonify({'success': False, 'message': 'Error deleting user'}), 500

@app.route('/api/students/<int:student_id>/status', methods=['PUT'])
@token_required
def update_student_status(current_user, student_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'}), 400
        
        student = db.session.get(Student, student_id)
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'}), 404

        old_status = student.status
        student.status = new_status

        db.session.commit()
        return jsonify({'success': True, 'message': 'Student status updated successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Error updating student status: {e}")
        return jsonify({'success': False, 'message': 'Error updating student status'}), 500

@app.route('/api/system/status', methods=['GET'])
def system_status():
    return jsonify({
        'success': True,
        'setup_required': False,
        'database_connected': True
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Institute Management System API',
        'status': 'running',
        'database_connected': True,
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
    
    with app.app_context():
        if os.environ.get('FLASK_RECREATE_DB') == 'True':
            print("⚠️ FLASK_RECREATE_DB is True: Dropping all database tables...")
            db.drop_all()
            print("✅ All database tables dropped.")

        db.create_all()
        init_default_data()
    print("✅ Database initialized and default data loaded successfully!")
    
    print("\n🌐 Server starting on http://localhost:5000")
    print("📱 Frontend should be on http://localhost:8000")
    print("\n" + "="*50)
    
    # For production, use:
    # app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
    # For development:
    app.run(debug=True, host='0.0.0.0', port=5000)
