"""
Helpdesk ML System - Flask Backend
Main application file with API routes and ML integration
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import joblib
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
CORS(app)

# Load ML Model
MODEL_PATH = 'models/ticket_classifier.pkl'
VECTORIZER_PATH = 'models/tfidf_vectorizer.pkl'

try:
    classifier = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    print("[SUCCESS] ML Model loaded successfully")
except Exception as e:
    print(f"[ERROR] Error loading ML model: {e}")
    classifier = None
    vectorizer = None

# Database Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Change this for production
    'database': 'helpdesk_ml_system'
}

def get_db_connection():
    """Create database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"Database connection error: {e}")
        return None

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_ticket_number():
    """Generate unique ticket number"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return f"TKT-{count + 1:04d}"
    return f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

def classify_ticket(text):
    """Classify ticket using ML model"""
    if classifier and vectorizer:
        try:
            text_vec = vectorizer.transform([text.lower()])
            category = classifier.predict(text_vec)[0]
            
            # Get confidence if available
            if hasattr(classifier, 'predict_proba'):
                proba = classifier.predict_proba(text_vec)
                confidence = max(proba[0]) * 100
            else:
                confidence = None
            
            return category, confidence
        except Exception as e:
            print(f"Classification error: {e}")
            return "Software", None
    return "Software", None

def assign_ticket_to_technician(ticket_id, category):
    """Auto-assign ticket to available technician based on skills"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    
    # Find available technician with matching skills
    query = """
        SELECT id, name, skills, current_workload 
        FROM technicians 
        WHERE availability_status = 'Available' 
        AND FIND_IN_SET(%s, skills) > 0
        ORDER BY current_workload ASC, id ASC
        LIMIT 1
    """
    
    cursor.execute(query, (category,))
    technician = cursor.fetchone()
    
    if technician:
        # Create assignment
        cursor.execute("""
            INSERT INTO assignments (ticket_id, technician_id) 
            VALUES (%s, %s)
        """, (ticket_id, technician['id']))
        
        # Update ticket status
        cursor.execute("""
            UPDATE tickets 
            SET status = 'Assigned' 
            WHERE id = %s
        """, (ticket_id,))
        
        # Update technician workload
        cursor.execute("""
            UPDATE technicians 
            SET current_workload = current_workload + 1 
            WHERE id = %s
        """, (technician['id']))
        
        conn.commit()
        cursor.close()
        conn.close()
        return technician
    
    cursor.close()
    conn.close()
    return None

# ============================================================
# ROUTES - Authentication
# ============================================================

@app.route('/')
def index():
    """Landing page"""
    if 'user_id' in session:
        if session.get('role') == 'user':
            return redirect(url_for('user_dashboard'))
        elif session.get('role') == 'technician':
            return redirect(url_for('technician_dashboard'))
        elif session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(dictionary=True)
        
        # Check credentials based on role
        if role == 'user':
            cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        elif role == 'technician':
            cursor.execute("SELECT * FROM technicians WHERE email = %s AND password = %s", (email, password))
        elif role == 'admin':
            cursor.execute("SELECT * FROM admins WHERE email = %s AND password = %s", (email, password))
        else:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Invalid role'}), 400
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = role
            
            if role == 'user':
                return redirect(url_for('user_dashboard'))
            elif role == 'technician':
                return redirect(url_for('technician_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('index'))

# ============================================================
# ROUTES - User Dashboard
# ============================================================

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    """User dashboard - submit and view tickets"""
    if session.get('role') != 'user':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        return render_template('user_dashboard.html', tickets=[])
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.*, 
               a.technician_id,
               tech.name as technician_name
        FROM tickets t
        LEFT JOIN assignments a ON t.id = a.ticket_id
        LEFT JOIN technicians tech ON a.technician_id = tech.id
        WHERE t.user_id = %s
        ORDER BY t.created_at DESC
    """, (session['user_id'],))
    
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('user_dashboard.html', tickets=tickets)

@app.route('/api/tickets/submit', methods=['POST'])
@login_required
def submit_ticket():
    """Submit new ticket with auto-classification"""
    data = request.get_json()
    
    subject = data.get('subject')
    description = data.get('description')
    priority = data.get('priority', 'Medium')
    
    if not subject or not description:
        return jsonify({'error': 'Subject and description are required'}), 400
    
    # Classify ticket using ML
    combined_text = f"{subject} {description}"
    category, confidence = classify_ticket(combined_text)
    
    # Generate ticket number
    ticket_number = generate_ticket_number()
    
    # Save ticket to database
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets (ticket_number, subject, description, category, priority, user_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'Open')
    """, (ticket_number, subject, description, category, priority, session['user_id']))
    
    ticket_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    # Auto-assign to technician
    assigned_tech = assign_ticket_to_technician(ticket_id, category)
    
    return jsonify({
        'success': True,
        'ticket_number': ticket_number,
        'ticket_id': ticket_id,
        'category': category,
        'confidence': f"{confidence:.2f}%" if confidence else "N/A",
        'assigned_to': assigned_tech['name'] if assigned_tech else 'Pending Assignment'
    }), 201

# ============================================================
# ROUTES - Technician Dashboard
# ============================================================

@app.route('/technician/dashboard')
@login_required
def technician_dashboard():
    """Technician dashboard - view assigned tickets"""
    if session.get('role') != 'technician':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        return render_template('technician_dashboard.html', tickets=[], stats={})
    
    cursor = conn.cursor(dictionary=True)
    
    # Get assigned tickets
    cursor.execute("""
        SELECT t.*, u.name as user_name, u.email as user_email, u.department,
               a.assigned_at
        FROM tickets t
        JOIN assignments a ON t.id = a.ticket_id
        JOIN users u ON t.user_id = u.id
        WHERE a.technician_id = %s
        ORDER BY t.priority DESC, t.created_at DESC
    """, (session['user_id'],))
    
    tickets = cursor.fetchall()
    
    # Get stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN t.status = 'Assigned' THEN 1 ELSE 0 END) as assigned,
            SUM(CASE WHEN t.status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN t.status = 'Resolved' THEN 1 ELSE 0 END) as resolved
        FROM tickets t
        JOIN assignments a ON t.id = a.ticket_id
        WHERE a.technician_id = %s
    """, (session['user_id'],))
    
    stats = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('technician_dashboard.html', tickets=tickets, stats=stats)

@app.route('/api/tickets/<int:ticket_id>/update-status', methods=['PUT'])
@login_required
def update_ticket_status(ticket_id):
    """Update ticket status"""
    data = request.get_json()
    new_status = data.get('status')
    notes = data.get('notes', '')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor()
    
    # Update ticket status
    cursor.execute("""
        UPDATE tickets 
        SET status = %s 
        WHERE id = %s
    """, (new_status, ticket_id))
    
    # Update assignment notes if provided
    if notes:
        cursor.execute("""
            UPDATE assignments 
            SET notes = %s 
            WHERE ticket_id = %s
        """, (notes, ticket_id))
    
    # If resolved, update completed_at and decrease workload
    if new_status == 'Resolved':
        cursor.execute("""
            UPDATE assignments 
            SET completed_at = NOW() 
            WHERE ticket_id = %s
        """, (ticket_id,))
        
        cursor.execute("""
            UPDATE technicians 
            SET current_workload = GREATEST(current_workload - 1, 0)
            WHERE id = %s
        """, (session['user_id'],))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Status updated successfully'})

# ============================================================
# ROUTES - Admin Dashboard
# ============================================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard - overview of all tickets"""
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if not conn:
        return render_template('admin_dashboard.html', stats={}, tickets=[])
    
    cursor = conn.cursor(dictionary=True)
    
    # Get overall stats
    cursor.execute("""
        SELECT 
            COUNT(*) as total_tickets,
            SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_tickets,
            SUM(CASE WHEN status = 'Assigned' THEN 1 ELSE 0 END) as assigned_tickets,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) as in_progress_tickets,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved_tickets,
            SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_tickets
        FROM tickets
    """)
    stats = cursor.fetchone()
    
    # Get category distribution
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM tickets
        GROUP BY category
    """)
    category_stats = cursor.fetchall()
    stats['categories'] = category_stats
    
    # Get recent tickets
    cursor.execute("""
        SELECT t.*, u.name as user_name, 
               tech.name as technician_name
        FROM tickets t
        JOIN users u ON t.user_id = u.id
        LEFT JOIN assignments a ON t.id = a.ticket_id
        LEFT JOIN technicians tech ON a.technician_id = tech.id
        ORDER BY t.created_at DESC
        LIMIT 20
    """)
    tickets = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_dashboard.html', stats=stats, tickets=tickets)

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """Get system statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    # Get stats
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM tickets) as total_tickets,
            (SELECT COUNT(*) FROM users) as total_users,
            (SELECT COUNT(*) FROM technicians) as total_technicians,
            (SELECT COUNT(*) FROM tickets WHERE status = 'Open') as open_tickets
    """)
    
    stats = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return jsonify(stats)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Helpdesk ML System Starting...")
    print("="*60)
    print("\nLogin Credentials for Testing:")
    print("-" * 40)
    print("USER:")
    print("  Email: john.doe@skanem.com")
    print("  Password: password123")
    print("\nTECHNICIAN:")
    print("  Email: mike.tech@skanem.com")
    print("  Password: tech123")
    print("\nADMIN:")
    print("  Email: admin@skanem.com")
    print("  Password: admin123")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
