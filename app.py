from flask import Flask, render_template, request, redirect
from pymysql import connections
import os
import boto3
import re
from botocore.exceptions import ClientError, NoCredentialsError
from config import *

app = Flask(__name__)
app.secret_key = 'aws-emp-management-secret-key-2024'

print("🚀 Initializing AWS Employee Management System...")

# Initialize AWS services
try:
    # RDS Database connection
    db_conn = connections.Connection(
        host=host,
        port=3306,
        user=user,
        password=password,
        db=db
    )
    print("✅ RDS Database connected successfully!")
except Exception as e:
    print(f"❌ RDS Connection failed: {e}")
    db_conn = None

# S3 Client with better error handling
s3_client = None
s3_bucket_exists = False
s3_access_denied = False

try:
    s3_client = boto3.client('s3', region_name=region)
    
    # Check if bucket exists and accessible
    try:
        s3_client.head_bucket(Bucket=bucket)
        s3_bucket_exists = True
        print(f"✅ S3 Bucket '{bucket}' is accessible!")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"❌ S3 Bucket '{bucket}' does not exist")
        elif error_code == '403':
            print(f"🔐 S3 Bucket exists but access denied - need permissions")
            s3_bucket_exists = True
            s3_access_denied = True
        else:
            print(f"❌ S3 Bucket error: {e}")
    except Exception as e:
        print(f"❌ S3 Client initialization failed: {e}")

except NoCredentialsError:
    print("❌ AWS credentials not found. Please configure AWS CLI or IAM role.")
except Exception as e:
    print(f"❌ S3 Client initialization failed: {e}")

# Create employees table if it doesn't exist
def create_employees_table():
    if not db_conn:
        print("❌ Cannot create table - no database connection")
        return False
    
    cursor = db_conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                emp_id VARCHAR(20) PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                pri_skill VARCHAR(200),
                location VARCHAR(100),
                image_url VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db_conn.commit()
        print("✅ Employees table created/verified successfully!")
        return True
    except Exception as e:
        print(f"❌ Table creation error: {e}")
        return False
    finally:
        cursor.close()

# Initialize table
if db_conn:
    create_employees_table()

def validate_emp_id(emp_id):
    return emp_id.isdigit() and len(emp_id) >= 3

def validate_name(name):
    return bool(re.match(r"^[A-Za-z\s]{2,50}$", name.strip()))

def upload_image_to_s3(image_file, emp_id):
    """Upload employee image to S3 and return public URL"""
    if not s3_client or not s3_bucket_exists:
        raise Exception("S3 service not available.")
    
    if s3_access_denied:
        raise Exception("S3 bucket access denied. Please check AWS permissions.")
    
    try:
        # Get file extension
        file_extension = os.path.splitext(image_file.filename)[1].lower()
        if file_extension not in ['.png', '.jpg', '.jpeg', '.gif']:
            raise Exception("Invalid file format. Use PNG, JPG, JPEG, or GIF.")
        
        # Create unique S3 key
        s3_key = f"employees/{emp_id}/profile{file_extension}"
        
        # Upload to S3
        s3_client.upload_fileobj(
            image_file,
            bucket,
            s3_key,
            ExtraArgs={
                'ContentType': 'image/jpeg' if file_extension in ['.jpg', '.jpeg'] else 'image/png',
                'ACL': 'public-read'
            }
        )
        
        # Generate public URL
        image_url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
        print(f"✅ Image uploaded to S3: {image_url}")
        return image_url
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            raise Exception(f"Access denied to S3 bucket. Please fix permissions.")
        elif error_code == 'InvalidAccessKeyId':
            raise Exception(f"AWS Access Key ID is invalid. Please check your credentials.")
        else:
            raise Exception(f"AWS S3 Error: {e}")
    except Exception as e:
        raise Exception(f"Upload Error: {e}")

def check_aws_services():
    """Check status of AWS services"""
    status = {
        'rds': False,
        's3': False,
        's3_bucket_exists': s3_bucket_exists,
        's3_access_denied': s3_access_denied
    }
    
    # Check RDS
    if db_conn:
        try:
            cursor = db_conn.cursor()
            cursor.execute("SELECT 1")
            status['rds'] = True
            cursor.close()
        except:
            status['rds'] = False
    
    # Check S3 - considered connected if bucket exists and no access denied
    status['s3'] = s3_bucket_exists and not s3_access_denied
    
    return status

@app.route("/")
def home():
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    aws_status = check_aws_services()
    return render_template('dashboard.html', 
                         aws_status=aws_status,
                         bucket=bucket,
                         region=region)

@app.route("/addemp", methods=['GET', 'POST'])
def AddEmp():
    if request.method == 'GET':
        aws_status = check_aws_services()
        return render_template('AddEmp.html', aws_status=aws_status)
    
    # Get form data
    emp_id = request.form.get('emp_id', '').strip()
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    pri_skill = request.form.get('pri_skill', '').strip()
    location = request.form.get('location', '').strip()
    emp_image_file = request.files.get('emp_image_file')
    
    # Validate inputs
    if not emp_id or not first_name or not last_name:
        return render_template('error.html', message="Employee ID, First Name, and Last Name are required.")
    
    if not validate_emp_id(emp_id):
        return render_template('error.html', message="Employee ID must contain only numbers (min 3 digits).")
    
    if not validate_name(first_name) or not validate_name(last_name):
        return render_template('error.html', message="Names must contain only letters (2-50 characters).")
    
    if not emp_image_file or emp_image_file.filename == '':
        return render_template('error.html', message="Please select a profile image.")
    
    # Check database connection
    if not db_conn:
        return render_template('error.html', message="Database connection unavailable.")
    
    # Check S3 availability
    aws_status = check_aws_services()
    if not aws_status['s3']:
        if aws_status['s3_access_denied']:
            return render_template('error.html', 
                                 message="S3 bucket access denied. Please fix AWS permissions.")
        else:
            return render_template('error.html', 
                                 message=f"S3 bucket '{bucket}' is not accessible.")
    
    cursor = db_conn.cursor()
    
    try:
        # Check if employee ID already exists
        cursor.execute("SELECT emp_id FROM employees WHERE emp_id = %s", (emp_id,))
        if cursor.fetchone():
            return render_template('error.html', 
                                 message=f"Employee ID {emp_id} already exists! Please use a different ID.")
        
        # Upload image to S3
        image_url = upload_image_to_s3(emp_image_file, emp_id)
        
        # Insert employee into database
        insert_sql = """
            INSERT INTO employees (emp_id, first_name, last_name, pri_skill, location, image_url) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location, image_url))
        db_conn.commit()
        
        emp_name = f"{first_name} {last_name}"
        print(f"✅ Employee {emp_name} (ID: {emp_id}) added successfully!")
        
        return render_template('add_employee.html', 
                             name=emp_name, 
                             emp_id=emp_id,
                             image_url=image_url)

    except Exception as e:
        if db_conn:
            db_conn.rollback()
        error_msg = str(e)
        print(f"❌ Error adding employee: {error_msg}")
        return render_template('error.html', message=error_msg)
    
    finally:
        cursor.close()

@app.route("/getemp", methods=['GET', 'POST'])
def getemp():
    return render_template('GetEmp.html')

@app.route("/fetchdata", methods=['POST'])
def GetEmp():
    if not db_conn:
        return render_template('error.html', message="Database connection unavailable.")
    
    search_type = request.form.get('search_type')
    search_value = request.form.get('search_value', '').strip()

    if not search_value:
        return render_template('error.html', message="Please enter a search value.")

    cursor = db_conn.cursor()
    
    try:
        if search_type == 'emp_id':
            if not search_value.isdigit():
                return render_template('error.html', message="Employee ID must be a number.")
            query = "SELECT * FROM employees WHERE emp_id = %s"
            cursor.execute(query, (search_value,))
        elif search_type == 'emp_name':
            query = "SELECT * FROM employees WHERE first_name LIKE %s OR last_name LIKE %s"
            search_pattern = f"%{search_value}%"
            cursor.execute(query, (search_pattern, search_pattern))
        elif search_type == 'primary_skills':
            query = "SELECT * FROM employees WHERE pri_skill LIKE %s"
            search_pattern = f"%{search_value}%"
            cursor.execute(query, (search_pattern,))
        else:
            return render_template('error.html', message="Invalid search type.")

        results = cursor.fetchall()
        
        if not results:
            return render_template('error.html', 
                                 message=f"No employees found matching '{search_value}'")
        
        return render_template('GetEmpOutput.html', output=results)
        
    except Exception as e:
        return render_template('error.html', message=f"Search error: {str(e)}")
    finally:
        cursor.close()

@app.route("/listemp", methods=['GET'])
def ListAllEmp():
    if not db_conn:
        return render_template('error.html', message="Database connection unavailable.")
    
    cursor = db_conn.cursor()
    try:
        cursor.execute("SELECT * FROM employees ORDER BY created_at DESC")
        results = cursor.fetchall()
        return render_template('ListAllEmp.html', output=results)
    except Exception as e:
        return render_template('error.html', message=f"Database error: {str(e)}")
    finally:
        cursor.close()

@app.route("/fix-s3")
def fix_s3():
    """Page with instructions to fix S3"""
    aws_status = check_aws_services()
    return render_template('fix_s3.html', 
                         aws_status=aws_status,
                         bucket=bucket,
                         region=region)

@app.route("/fix-permissions")
def fix_permissions():
    """Endpoint to fix S3 permissions"""
    try:
        s3 = boto3.client('s3', region_name=region)
        
        # Remove public access blocks
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        
        return "✅ S3 permissions fixed! Please restart the application."
    except Exception as e:
        return f"❌ Error fixing permissions: {e}"

@app.route("/health")
def health_check():
    """Health check endpoint"""
    aws_status = check_aws_services()
    return {
        "status": "healthy" if aws_status['rds'] else "degraded",
        "database": "connected" if aws_status['rds'] else "disconnected",
        "s3": "connected" if aws_status['s3'] else "disconnected",
        "s3_bucket_exists": aws_status['s3_bucket_exists'],
        "s3_access_denied": aws_status['s3_access_denied']
    }

@app.route("/aws-status")
def aws_status():
    """AWS services status page"""
    aws_status = check_aws_services()
    return render_template('aws_status.html', 
                         aws_status=aws_status,
                         bucket=bucket,
                         region=region,
                         host=host)

if __name__ == '__main__':
    print("=" * 60)
    print("🏢 AWS Employee Management System")
    print("=" * 60)
    print(f"📍 AWS Region: {region}")
    print(f"🗄️  RDS Database: {host}")
    print(f"📦 S3 Bucket: {bucket} - {'✅ EXISTS' if s3_bucket_exists else '❌ MISSING'}")
    if s3_access_denied:
        print(f"🔐 S3 Access: ❌ DENIED - Need permissions")
    print("=" * 60)
    
    status = check_aws_services()
    print(f"✅ RDS Status: {'Connected' if status['rds'] else 'Disconnected'}")
    print(f"✅ S3 Status: {'Connected' if status['s3'] else 'Disconnected'}")
    
    if status['s3_access_denied']:
        print("\n🔐 S3 Access Denied! Visit http://localhost:8080/fix-s3 for instructions")
    elif not status['s3_bucket_exists']:
        print("\n⚠️  S3 Bucket is missing! Visit http://localhost:8080/fix-s3 for instructions")
    
    print("=" * 60)
    print("🌐 Starting server at http://localhost:8080")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=8080, debug=True)