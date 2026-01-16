"""
Helpdesk ML System - Demo Version (SQLite)
Quick demo without MySQL requirement
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import sqlite3
from datetime import datetime
import joblib
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'demo-secret-key'

# Initialize Socket.IO for real-time notifications
socketio = SocketIO(app, cors_allowed_origins="*")

# Load ML Model
MODEL_PATH = 'models/ticket_classifier.pkl'
VECTORIZER_PATH = 'models/tfidf_vectorizer.pkl'
DB_PATH = 'demo_helpdesk.db'

try:
    classifier = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    print("[SUCCESS] ML Model loaded successfully")
except Exception as e:
    print(f"[ERROR] Error loading ML model: {e}")
    classifier = None
    vectorizer = None

def get_db_connection():
    """Create SQLite database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database with schema and sample data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            department TEXT,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS technicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            skills TEXT,
            current_workload INTEGER DEFAULT 0,
            availability_status TEXT DEFAULT 'Available',
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Open',
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL,
            technician_id INTEGER NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id),
            FOREIGN KEY (technician_id) REFERENCES technicians(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample data if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO users (name, email, phone, department, password) VALUES
            ('John Doe', 'john.doe@skanem.com', '+254712345678', 'Production', 'password123'),
            ('Jane Smith', 'jane.smith@skanem.com', '+254723456789', 'Quality Control', 'password123'),
            ('Bob Wilson', 'bob.wilson@skanem.com', '+254734567890', 'Logistics', 'password123')
        """)
        
        cursor.execute("""
            INSERT INTO technicians (name, email, phone, skills, password) VALUES
            ('Tech Mike', 'mike.tech@skanem.com', '+254745678901', 'Hardware,Network', 'tech123'),
            ('Tech Sarah', 'sarah.tech@skanem.com', '+254756789012', 'Software,Database', 'tech123'),
            ('Tech James', 'james.tech@skanem.com', '+254767890123', 'Hardware,Software,Network', 'tech123')
        """)
        
        cursor.execute("""
            INSERT INTO admins (name, email, password) VALUES
            ('Admin User', 'admin@skanem.com', 'admin123')
        """)
        
        cursor.execute("""
            INSERT INTO tickets (ticket_number, subject, description, category, priority, user_id, status) VALUES
            ('TKT-0001', 'Printer not working', 'Office printer on floor 2 is not responding', 'Hardware', 'Medium', 1, 'Open'),
            ('TKT-0002', 'Email access issues', 'Cannot access my email account since this morning', 'Software', 'High', 2, 'Open'),
            ('TKT-0003', 'Internet connection down', 'No internet connection in production area', 'Network', 'Critical', 3, 'Open')
        """)
    
    conn.commit()
    conn.close()
    print("[SUCCESS] Database initialized")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_ticket_number():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tickets")
    count = cursor.fetchone()[0]
    conn.close()
    return f"TKT-{count + 1:04d}"

def classify_ticket(text):
    if classifier and vectorizer:
        try:
            text_vec = vectorizer.transform([text.lower()])
            category = classifier.predict(text_vec)[0]
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
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, skills, current_workload 
        FROM technicians 
        WHERE availability_status = 'Available' 
        AND skills LIKE ?
        ORDER BY current_workload ASC, id ASC
        LIMIT 1
    """, (f'%{category}%',))
    
    technician = cursor.fetchone()
    
    if technician:
        cursor.execute("""
            INSERT INTO assignments (ticket_id, technician_id) 
            VALUES (?, ?)
        """, (ticket_id, technician['id']))
        
        cursor.execute("""
            UPDATE tickets 
            SET status = 'Assigned' 
            WHERE id = ?
        """, (ticket_id,))
        
        cursor.execute("""
            UPDATE technicians 
            SET current_workload = current_workload + 1 
            WHERE id = ?
        """, (technician['id'],))
        
        # Get ticket details for real-time notification
        cursor.execute("""
            SELECT ticket_number, subject, category, priority
            FROM tickets
            WHERE id = ?
        """, (ticket_id,))
        ticket_info = cursor.fetchone()
        
        conn.commit()
        result = dict(technician)
        conn.close()
        
        # Send real-time Socket.IO notification
        if ticket_info:
            try:
                socketio.emit('new_ticket_assigned', {
                    'technician_id': technician['id'],
                    'ticket_id': ticket_id,
                    'ticket_number': ticket_info['ticket_number'],
                    'subject': ticket_info['subject'],
                    'category': ticket_info['category'],
                    'priority': ticket_info['priority'],
                    'message': f"New {ticket_info['priority']} priority ticket assigned: {ticket_info['ticket_number']}"
                }, broadcast=True)
                print(f"[NOTIFICATION] Sent to technician {technician['id']}: {ticket_info['ticket_number']}")
            except Exception as e:
                print(f"[ERROR] Socket.IO notification failed: {e}")
        
        return result
    
    conn.close()
    return None

# Routes
@app.route('/')
def index():
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
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if role == 'user':
            cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        elif role == 'technician':
            cursor.execute("SELECT * FROM technicians WHERE email = ? AND password = ?", (email, password))
        elif role == 'admin':
            cursor.execute("SELECT * FROM admins WHERE email = ? AND password = ?", (email, password))
        else:
            conn.close()
            return jsonify({'error': 'Invalid role'}), 400
        
        user = cursor.fetchone()
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
    session.clear()
    return redirect(url_for('index'))

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, 
               a.technician_id,
               tech.name as technician_name
        FROM tickets t
        LEFT JOIN assignments a ON t.id = a.ticket_id
        LEFT JOIN technicians tech ON a.technician_id = tech.id
        WHERE t.user_id = ?
        ORDER BY t.created_at DESC
    """, (session['user_id'],))
    
    tickets = [dict(row) for row in cursor.fetchall()]
    
    # Convert datetime strings to formatted strings for SQLite
    for ticket in tickets:
        if ticket.get('created_at'):
            # SQLite returns datetime as string, format it nicely
            ticket['created_at_formatted'] = ticket['created_at'][:16].replace('T', ' ')
        if ticket.get('updated_at'):
            ticket['updated_at_formatted'] = ticket['updated_at'][:16].replace('T', ' ')
    
    conn.close()
    
    return render_template('user_dashboard.html', tickets=tickets)

@app.route('/api/tickets/submit', methods=['POST'])
@login_required
def submit_ticket():
    data = request.get_json()
    
    subject = data.get('subject')
    description = data.get('description')
    priority = data.get('priority', 'Medium')
    
    if not subject or not description:
        return jsonify({'error': 'Subject and description are required'}), 400
    
    combined_text = f"{subject} {description}"
    category, confidence = classify_ticket(combined_text)
    ticket_number = generate_ticket_number()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets (ticket_number, subject, description, category, priority, user_id, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Open')
    """, (ticket_number, subject, description, category, priority, session['user_id']))
    
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    assigned_tech = assign_ticket_to_technician(ticket_id, category)
    
    return jsonify({
        'success': True,
        'ticket_number': ticket_number,
        'ticket_id': ticket_id,
        'category': category,
        'confidence': f"{confidence:.2f}%" if confidence else "N/A",
        'assigned_to': assigned_tech['name'] if assigned_tech else 'Pending Assignment'
    }), 201

@app.route('/technician/dashboard')
@login_required
def technician_dashboard():
    if session.get('role') != 'technician':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.*, u.name as user_name, u.email as user_email, u.department,
               a.assigned_at
        FROM tickets t
        JOIN assignments a ON t.id = a.ticket_id
        JOIN users u ON t.user_id = u.id
        WHERE a.technician_id = ?
        ORDER BY t.priority DESC, t.created_at DESC
    """, (session['user_id'],))
    
    tickets = [dict(row) for row in cursor.fetchall()]
    
    # Format datetime strings for SQLite
    for ticket in tickets:
        if ticket.get('created_at'):
            ticket['created_at_formatted'] = ticket['created_at'][:16].replace('T', ' ')
        if ticket.get('assigned_at'):
            ticket['assigned_at_formatted'] = ticket['assigned_at'][:16].replace('T', ' ')
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN t.status = 'Assigned' THEN 1 ELSE 0 END) as assigned,
            SUM(CASE WHEN t.status = 'In Progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN t.status = 'Resolved' THEN 1 ELSE 0 END) as resolved
        FROM tickets t
        JOIN assignments a ON t.id = a.ticket_id
        WHERE a.technician_id = ?
    """, (session['user_id'],))
    
    stats = dict(cursor.fetchone())
    conn.close()
    
    return render_template('technician_dashboard.html', tickets=tickets, stats=stats)

@app.route('/api/tickets/<int:ticket_id>/update-status', methods=['PUT'])
@login_required
def update_ticket_status(ticket_id):
    data = request.get_json()
    new_status = data.get('status')
    notes = data.get('notes', '')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE tickets 
        SET status = ? 
        WHERE id = ?
    """, (new_status, ticket_id))
    
    if notes:
        cursor.execute("""
            UPDATE assignments 
            SET notes = ? 
            WHERE ticket_id = ?
        """, (notes, ticket_id))
    
    if new_status == 'Resolved':
        cursor.execute("""
            UPDATE assignments 
            SET completed_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
        """, (ticket_id,))
        
        cursor.execute("""
            UPDATE technicians 
            SET current_workload = MAX(current_workload - 1, 0)
            WHERE id = ?
        """, (session['user_id'],))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Status updated successfully'})

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    stats = dict(cursor.fetchone())
    
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM tickets
        GROUP BY category
    """)
    stats['categories'] = [dict(row) for row in cursor.fetchall()]
    
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
    tickets = [dict(row) for row in cursor.fetchall()]
    
    # Format datetime strings for SQLite
    for ticket in tickets:
        if ticket.get('created_at'):
            ticket['created_at_formatted'] = ticket['created_at'][:16].replace('T', ' ')
    
    conn.close()
    
    return render_template('admin_dashboard.html', stats=stats, tickets=tickets)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Helpdesk ML System - DEMO VERSION (SQLite)")
    print("="*60)
    
    # Initialize database
    if not os.path.exists(DB_PATH):
        print("\nInitializing database...")
        init_db()
    
    print("\nLogin Credentials:")
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
    print("Real-time notifications: ENABLED")
    print("="*60 + "\n")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
