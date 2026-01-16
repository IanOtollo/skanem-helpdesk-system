"""
SKANEM INTERLABELS AFRICA - HELPDESK SYSTEM
Production Version with Full Security & Railway Deployment
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import sqlite3
from datetime import datetime
import joblib
import os
import json
from functools import wraps
import bcrypt

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'demo-secret-key-change-in-production')

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Database
DB_PATH = 'helpdesk.db'

# ML Model configuration
MODEL_DIR = 'models/'
MODEL_PATH = os.path.join(MODEL_DIR, 'ticket_classifier.pkl')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
METADATA_PATH = os.path.join(MODEL_DIR, 'model_metadata.pkl')

# Confidence threshold
CONFIDENCE_THRESHOLD = 0.60

# Load ML models
try:
    ml_model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(VECTORIZER_PATH)
    model_metadata = joblib.load(METADATA_PATH)
    print(f"✓ ML Model loaded: {model_metadata.get('model_version', 'Unknown')}")
except Exception as e:
    print(f"⚠️  ML Model not found. Manual assignment will be used.")
    ml_model = None
    vectorizer = None
    model_metadata = {}

# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except:
        return False

def log_system_action(log_type, action, details=None, user_type=None, user_id=None, status='success'):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_logs (log_type, user_type, user_id, action, details, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (log_type, user_type, user_id, action, details, status))
        conn.commit()
    except:
        pass
    finally:
        conn.close()

def create_notification(user_type, user_id, ticket_id, notification_type, title, message):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notifications (user_type, user_id, ticket_id, notification_type, title, message)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_type, user_id, ticket_id, notification_type, title, message))
        conn.commit()
    except:
        pass
    finally:
        conn.close()

# =============================================================================
# ML FUNCTIONS
# =============================================================================

def classify_ticket_with_confidence(subject, description):
    if not ml_model or not vectorizer:
        return None, 0.0, True
    
    try:
        text = f"{subject} {description}".lower().strip()
        text_vec = vectorizer.transform([text])
        category = ml_model.predict(text_vec)[0]
        probabilities = ml_model.predict_proba(text_vec)[0]
        confidence = probabilities.max()
        confidence_pct = round(confidence * 100, 2)
        needs_manual_review = confidence < CONFIDENCE_THRESHOLD
        return category, confidence_pct, needs_manual_review
    except:
        return None, 0.0, True

# =============================================================================
# AUTHENTICATION
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================================================================
# TICKET ASSIGNMENT
# =============================================================================

def assign_ticket_to_technician(ticket_id, category, is_manual=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, skills, current_workload 
        FROM technicians 
        WHERE availability_status = 'Available' 
        AND skills LIKE ?
        AND is_active = TRUE
        ORDER BY current_workload ASC
        LIMIT 1
    """, (f'%{category}%',))
    
    technician = cursor.fetchone()
    
    if technician:
        assigned_by = 'Admin' if is_manual else 'System'
        cursor.execute("""
            INSERT INTO assignments (ticket_id, technician_id, assigned_by) 
            VALUES (?, ?, ?)
        """, (ticket_id, technician['id'], assigned_by))
        
        cursor.execute("""
            UPDATE tickets 
            SET status = 'Assigned', assigned_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (ticket_id,))
        
        cursor.execute("""
            UPDATE technicians 
            SET current_workload = current_workload + 1 
            WHERE id = ?
        """, (technician['id'],))
        
        cursor.execute("""
            SELECT ticket_number, subject, category, priority
            FROM tickets WHERE id = ?
        """, (ticket_id,))
        ticket_info = cursor.fetchone()
        
        conn.commit()
        
        if ticket_info:
            create_notification(
                'technician', technician['id'], ticket_id,
                'ticket_assigned', 'New Ticket Assigned',
                f"Ticket {ticket_info['ticket_number']}: {ticket_info['subject']}"
            )
            
            try:
                socketio.emit('new_ticket_assigned', {
                    'technician_id': technician['id'],
                    'ticket_id': ticket_id,
                    'ticket_number': ticket_info['ticket_number'],
                    'subject': ticket_info['subject'],
                    'category': ticket_info['category'],
                    'priority': ticket_info['priority'],
                    'assigned_by': assigned_by,
                    'message': f"New {ticket_info['priority']} priority ticket assigned"
                }, broadcast=True)
            except:
                pass
        
        result = dict(technician)
        conn.close()
        return result
    
    conn.close()
    return None

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
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
            cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = TRUE", (email,))
        elif role == 'technician':
            cursor.execute("SELECT * FROM technicians WHERE email = ? AND is_active = TRUE", (email,))
        elif role == 'admin':
            cursor.execute("SELECT * FROM admins WHERE email = ? AND is_active = TRUE", (email,))
        else:
            conn.close()
            return render_template('login.html', error='Invalid role')
        
        user = cursor.fetchone()
        
        if user and verify_password(password, user['password_hash']):
            table_name = 'users' if role == 'user' else ('technicians' if role == 'technician' else 'admins')
            cursor.execute(f"UPDATE {table_name} SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
            conn.commit()
            
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = role
            
            log_system_action('login', f"{role.title()} login successful", f"User: {user['email']}", role, user['id'], 'success')
            
            conn.close()
            
            if role == 'user':
                return redirect(url_for('user_dashboard'))
            elif role == 'technician':
                return redirect(url_for('technician_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))
        else:
            log_system_action('login', 'Login failed', f"Email: {email}, Role: {role}", status='failure')
            conn.close()
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    user_type = session.get('role')
    user_id = session.get('user_id')
    log_system_action('logout', 'User logged out', user_type=user_type, user_id=user_id)
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
               tech.name as technician_name,
               tech.phone as technician_phone
        FROM tickets t
        LEFT JOIN assignments a ON t.id = a.ticket_id AND a.is_active = TRUE
        LEFT JOIN technicians tech ON a.technician_id = tech.id
        WHERE t.user_id = ?
        ORDER BY t.submitted_at DESC
    """, (session['user_id'],))
    
    tickets = []
    for row in cursor.fetchall():
        ticket = dict(row)
        ticket['created_at_formatted'] = datetime.strptime(
            ticket['submitted_at'], '%Y-%m-%d %H:%M:%S'
        ).strftime('%Y-%m-%d %H:%M')
        tickets.append(ticket)
    
    conn.close()
    
    return render_template('user_dashboard.html', tickets=tickets)

@app.route('/technician/dashboard')
@login_required
def technician_dashboard():
    if session.get('role') != 'technician':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT current_workload, total_tickets_resolved, average_resolution_time
        FROM technicians WHERE id = ?
    """, (session['user_id'],))
    tech_info = cursor.fetchone()
    
    cursor.execute("""
        SELECT t.*, 
               u.name as user_name,
               u.email as user_email,
               u.phone as user_phone,
               u.department as user_department,
               a.assigned_at,
               a.notes
        FROM tickets t
        JOIN assignments a ON t.id = a.ticket_id
        JOIN users u ON t.user_id = u.id
        WHERE a.technician_id = ? 
        AND a.is_active = TRUE
        AND t.status != 'Closed'
        ORDER BY 
            CASE t.priority
                WHEN 'Critical' THEN 1
                WHEN 'High' THEN 2
                WHEN 'Medium' THEN 3
                WHEN 'Low' THEN 4
            END,
            t.submitted_at ASC
    """, (session['user_id'],))
    
    tickets = []
    for row in cursor.fetchall():
        ticket = dict(row)
        ticket['created_at_formatted'] = datetime.strptime(
            ticket['submitted_at'], '%Y-%m-%d %H:%M:%S'
        ).strftime('%Y-%m-%d %H:%M')
        tickets.append(ticket)
    
    stats = {
        'assigned': len([t for t in tickets if t['status'] == 'Assigned']),
        'in_progress': len([t for t in tickets if t['status'] == 'In Progress']),
        'total': len(tickets),
        'workload': tech_info['current_workload'] if tech_info else 0
    }
    
    conn.close()
    
    return render_template('technician_dashboard.html', tickets=tickets, stats=stats)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM tickets")
    total_tickets = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as open FROM tickets WHERE status NOT IN ('Resolved', 'Closed')")
    open_tickets = cursor.fetchone()['open']
    
    cursor.execute("SELECT COUNT(*) as resolved FROM tickets WHERE status = 'Resolved'")
    resolved_tickets = cursor.fetchone()['resolved']
    
    cursor.execute("""
        SELECT COUNT(*) as flagged 
        FROM tickets 
        WHERE flagged_for_manual_review = TRUE 
        AND status NOT IN ('Assigned', 'In Progress', 'Resolved', 'Closed')
    """)
    flagged_tickets = cursor.fetchone()['flagged']
    
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM tickets 
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
    """)
    categories = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT t.*, u.name as user_name, u.department
        FROM tickets t
        JOIN users u ON t.user_id = u.id
        WHERE t.flagged_for_manual_review = TRUE
        AND t.status NOT IN ('Assigned', 'In Progress', 'Resolved', 'Closed')
        ORDER BY t.submitted_at DESC
    """)
    flagged_list = []
    for row in cursor.fetchall():
        ticket = dict(row)
        ticket['created_at_formatted'] = datetime.strptime(
            ticket['submitted_at'], '%Y-%m-%d %H:%M:%S'
        ).strftime('%Y-%m-%d %H:%M')
        flagged_list.append(ticket)
    
    cursor.execute("""
        SELECT t.*,
               u.name as user_name,
               tech.name as technician_name
        FROM tickets t
        LEFT JOIN users u ON t.user_id = u.id
        LEFT JOIN assignments a ON t.id = a.ticket_id AND a.is_active = TRUE
        LEFT JOIN technicians tech ON a.technician_id = tech.id
        ORDER BY t.submitted_at DESC
        LIMIT 50
    """)
    all_tickets = []
    for row in cursor.fetchall():
        ticket = dict(row)
        ticket['created_at_formatted'] = datetime.strptime(
            ticket['submitted_at'], '%Y-%m-%d %H:%M:%S'
        ).strftime('%Y-%m-%d %H:%M')
        all_tickets.append(ticket)
    
    cursor.execute("""
        SELECT id, name, skills, current_workload, max_workload
        FROM technicians
        WHERE is_active = TRUE
        ORDER BY current_workload ASC
    """)
    technicians = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT model_version, accuracy, training_date, is_active
        FROM model_logs
        WHERE is_active = TRUE
        ORDER BY training_date DESC
        LIMIT 1
    """)
    model_info = cursor.fetchone()
    if model_info:
        model_info = dict(model_info)
    
    stats = {
        'total': total_tickets,
        'open': open_tickets,
        'resolved': resolved_tickets,
        'flagged': flagged_tickets
    }
    
    conn.close()
    
    return render_template(
        'admin_dashboard.html',
        stats=stats,
        categories=categories,
        flagged_tickets=flagged_list,
        all_tickets=all_tickets,
        technicians=technicians,
        model_info=model_info,
        confidence_threshold=CONFIDENCE_THRESHOLD * 100
    )

# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/api/tickets/submit', methods=['POST'])
@login_required
def submit_ticket():
    if session.get('role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # FIX: Get JSON data instead of form data
    data = request.get_json()
    subject = data.get('subject') if data else None
    description = data.get('description') if data else None
    priority = data.get('priority', 'Medium') if data else 'Medium'
    
    if not subject or not description:
        return jsonify({'error': 'Subject and description required'}), 400
    
    category, confidence_score, needs_manual_review = classify_ticket_with_confidence(subject, description)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    ticket_number = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        cursor.execute("""
            INSERT INTO tickets (
                ticket_number, subject, description, category, priority,
                user_id, confidence_score, flagged_for_manual_review, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticket_number, subject, description, category, priority,
              session['user_id'], confidence_score, needs_manual_review, 'Classified'))
        
        ticket_id = cursor.lastrowid
        
        cursor.execute("UPDATE tickets SET classified_at = CURRENT_TIMESTAMP WHERE id = ?", (ticket_id,))
        conn.commit()
        
        assigned_technician = None
        if not needs_manual_review and category:
            assigned_technician = assign_ticket_to_technician(ticket_id, category, is_manual=False)
        
        conn.close()
        
        response_data = {
            'success': True,
            'ticket_number': ticket_number,
            'category': category,
            'confidence': f"{confidence_score}%",
            'needs_manual_review': needs_manual_review
        }
        
        if assigned_technician:
            response_data['assigned_to'] = assigned_technician['name']
            response_data['status'] = 'Assigned'
        else:
            response_data['status'] = 'Awaiting Assignment' if needs_manual_review else 'Classified'
        
        return jsonify(response_data), 201
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/tickets/<int:ticket_id>/update-status', methods=['PUT'])
@login_required
def update_ticket_status(ticket_id):
    if session.get('role') != 'technician':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    notes = data.get('notes', '')
    
    if new_status not in ['Assigned', 'In Progress', 'Resolved']:
        return jsonify({'error': 'Invalid status'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT a.id FROM assignments a
            WHERE a.ticket_id = ? AND a.technician_id = ? AND a.is_active = TRUE
        """, (ticket_id, session['user_id']))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Unauthorized'}), 403
        
        cursor.execute("UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id))
        
        if notes:
            cursor.execute("""
                UPDATE assignments 
                SET notes = ?, resolution_notes = ?
                WHERE ticket_id = ? AND technician_id = ? AND is_active = TRUE
            """, (notes, notes, ticket_id, session['user_id']))
        
        if new_status == 'In Progress':
            cursor.execute("UPDATE tickets SET in_progress_at = CURRENT_TIMESTAMP WHERE id = ? AND in_progress_at IS NULL", (ticket_id,))
        elif new_status == 'Resolved':
            cursor.execute("UPDATE tickets SET resolved_at = CURRENT_TIMESTAMP WHERE id = ? AND resolved_at IS NULL", (ticket_id,))
            cursor.execute("UPDATE assignments SET completed_at = CURRENT_TIMESTAMP WHERE ticket_id = ? AND technician_id = ?", (ticket_id, session['user_id']))
            cursor.execute("UPDATE technicians SET total_tickets_resolved = total_tickets_resolved + 1, current_workload = current_workload - 1 WHERE id = ?", (session['user_id'],))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'status': new_status})
    except:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Error'}), 500

@app.route('/api/admin/assign-ticket', methods=['POST'])
@login_required
def manual_assign_ticket():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    technician_id = data.get('technician_id')
    reason = data.get('reason', 'Manual assignment by admin')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket:
            conn.close()
            return jsonify({'error': 'Ticket not found'}), 404
        
        cursor.execute("INSERT INTO assignments (ticket_id, technician_id, assigned_by) VALUES (?, ?, 'Admin')", (ticket_id, technician_id))
        cursor.execute("UPDATE tickets SET status = 'Assigned', assigned_at = CURRENT_TIMESTAMP, flagged_for_manual_review = FALSE, manual_assignment_reason = ? WHERE id = ?", (reason, ticket_id))
        cursor.execute("UPDATE technicians SET current_workload = current_workload + 1 WHERE id = ?", (technician_id,))
        
        conn.commit()
        
        create_notification('technician', technician_id, ticket_id, 'ticket_assigned', 'New Ticket Manually Assigned', f"Admin assigned ticket {ticket['ticket_number']} to you")
        
        try:
            socketio.emit('new_ticket_assigned', {
                'technician_id': technician_id,
                'ticket_id': ticket_id,
                'ticket_number': ticket['ticket_number'],
                'subject': ticket['subject'],
                'category': ticket['category'],
                'priority': ticket['priority'],
                'assigned_by': 'Admin',
                'message': f"Manual assignment: {ticket['ticket_number']}"
            }, broadcast=True)
        except:
            pass
        
        conn.close()
        return jsonify({'success': True})
    except:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Error'}), 500

@app.route('/api/admin/close-ticket/<int:ticket_id>', methods=['POST'])
@login_required
def close_ticket(ticket_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        
        if not ticket or ticket['status'] != 'Resolved':
            conn.close()
            return jsonify({'error': 'Only resolved tickets can be closed'}), 400
        
        cursor.execute("UPDATE tickets SET status = 'Closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?", (ticket_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except:
        conn.rollback()
        conn.close()
        return jsonify({'error': 'Error'}), 500

# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("SKANEM INTERLABELS AFRICA - HELPDESK SYSTEM")
    print("="*70)
    print("\n✓ Security: Bcrypt password hashing ENABLED")
    print(f"✓ ML Confidence threshold: {CONFIDENCE_THRESHOLD*100}%")
    print("✓ Manual review: Automatic flagging")
    print("✓ Real-time notifications: Socket.IO ENABLED")
    print("✓ Complete lifecycle: 6 stages (including Closed)")
    print("\n" + "="*70)
    print("Login Credentials:")
    print("-"*70)
    print("\nUSER:")
    print("  Email: john.doe@skanem.com")
    print("  Password: password123")
    print("\nTECHNICIAN:")
    print("  Email: mike.tech@skanem.com")
    print("  Password: tech123")
    print("\nADMIN:")
    print("  Email: admin@skanem.com")
    print("  Password: admin123")
    print("\n" + "="*70 + "\n")
    
    # CRITICAL: Read PORT from Railway environment
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on 0.0.0.0:{port}\n")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=port)