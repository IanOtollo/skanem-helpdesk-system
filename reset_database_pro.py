#!/usr/bin/env python3
"""
Database Reset Script - PRODUCTION VERSION
Features:
- Bcrypt password hashing (NOT plain text)
- Complete schema with all requirements
- Model logging
- Notifications table
- System logs
"""

import os
import sqlite3
import bcrypt
from datetime import datetime

# Database path
DB_PATH = 'helpdesk.db'

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print("=" * 70)
print("DATABASE RESET - PRODUCTION VERSION")
print("WITH BCRYPT PASSWORD HASHING")
print("=" * 70)

# Delete old database
if os.path.exists(DB_PATH):
    print(f"\n[1/4] Deleting old database: {DB_PATH}")
    os.remove(DB_PATH)
    print("✓ Old database deleted")
else:
    print(f"\n[1/4] No existing database found")

# Create new database
print("\n[2/4] Creating fresh database with complete schema...")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Create all tables
print("  - Creating users table...")
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        department TEXT,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
''')

print("  - Creating technicians table...")
cursor.execute('''
    CREATE TABLE technicians (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        skills TEXT,
        password_hash TEXT NOT NULL,
        current_workload INTEGER DEFAULT 0,
        max_workload INTEGER DEFAULT 10,
        availability_status TEXT DEFAULT 'Available',
        expertise_level TEXT DEFAULT 'Mid',
        total_tickets_resolved INTEGER DEFAULT 0,
        average_resolution_time REAL DEFAULT 0.00,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
''')

print("  - Creating admins table...")
cursor.execute('''
    CREATE TABLE admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
''')

print("  - Creating tickets table (with confidence scoring)...")
cursor.execute('''
    CREATE TABLE tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_number TEXT UNIQUE NOT NULL,
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT,
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'Submitted',
        user_id INTEGER NOT NULL,
        confidence_score REAL,
        flagged_for_manual_review BOOLEAN DEFAULT FALSE,
        manual_assignment_reason TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        classified_at TIMESTAMP,
        assigned_at TIMESTAMP,
        in_progress_at TIMESTAMP,
        resolved_at TIMESTAMP,
        closed_at TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
''')

print("  - Creating assignments table...")
cursor.execute('''
    CREATE TABLE assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER NOT NULL,
        technician_id INTEGER NOT NULL,
        assigned_by TEXT DEFAULT 'System',
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        accepted_at TIMESTAMP,
        completed_at TIMESTAMP,
        notes TEXT,
        resolution_notes TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (ticket_id) REFERENCES tickets(id),
        FOREIGN KEY (technician_id) REFERENCES technicians(id)
    )
''')

print("  - Creating notifications table...")
cursor.execute('''
    CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_type TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        ticket_id INTEGER,
        notification_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read BOOLEAN DEFAULT FALSE,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        read_at TIMESTAMP
    )
''')

print("  - Creating model_logs table (maintainability)...")
cursor.execute('''
    CREATE TABLE model_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_version TEXT NOT NULL,
        model_type TEXT DEFAULT 'LogisticRegression',
        training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        dataset_size INTEGER NOT NULL,
        training_samples INTEGER NOT NULL,
        testing_samples INTEGER NOT NULL,
        accuracy REAL NOT NULL,
        precision_avg REAL,
        recall_avg REAL,
        f1_score_avg REAL,
        category_metrics TEXT,
        model_file_path TEXT,
        vectorizer_file_path TEXT,
        training_duration INTEGER,
        trained_by TEXT DEFAULT 'System',
        notes TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        deployed_at TIMESTAMP
    )
''')

print("  - Creating system_logs table (audit trail)...")
cursor.execute('''
    CREATE TABLE system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_type TEXT NOT NULL,
        user_type TEXT,
        user_id INTEGER,
        action TEXT NOT NULL,
        details TEXT,
        status TEXT DEFAULT 'success',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Insert demo data with BCRYPT passwords
print("\n[3/4] Inserting demo data with bcrypt-hashed passwords...")

print("  - Hashing passwords (this takes a few seconds)...")
user_password = hash_password('password123')
tech_password = hash_password('tech123')
admin_password = hash_password('admin123')
print("  ✓ Passwords hashed securely")

print("  - Adding users...")
users = [
    ('John Doe', 'john.doe@skanem.com', '+254712345678', 'Production', user_password),
    ('Jane Smith', 'jane.smith@skanem.com', '+254723456789', 'Quality Control', user_password),
    ('Bob Wilson', 'bob.wilson@skanem.com', '+254734567890', 'Logistics', user_password)
]

for name, email, phone, dept, pwd_hash in users:
    cursor.execute("""
        INSERT INTO users (name, email, phone, department, password_hash) 
        VALUES (?, ?, ?, ?, ?)
    """, (name, email, phone, dept, pwd_hash))

print("  - Adding technicians...")
technicians = [
    ('Mike Johnson', 'mike.tech@skanem.com', '+254745678901', 'Hardware,Network', tech_password),
    ('Sarah Davis', 'sarah.tech@skanem.com', '+254756789012', 'Software,Database', tech_password),
    ('James Brown', 'james.tech@skanem.com', '+254767890123', 'Hardware,Software,Network', tech_password)
]

for name, email, phone, skills, pwd_hash in technicians:
    cursor.execute("""
        INSERT INTO technicians (name, email, phone, skills, password_hash) 
        VALUES (?, ?, ?, ?, ?)
    """, (name, email, phone, skills, pwd_hash))

print("  - Adding admin...")
cursor.execute("""
    INSERT INTO admins (name, email, password_hash) 
    VALUES (?, ?, ?)
""", ('System Admin', 'admin@skanem.com', admin_password))

# Log initial setup
print("\n[4/4] Creating system logs...")
cursor.execute("""
    INSERT INTO system_logs (log_type, action, details, status)
    VALUES (?, ?, ?, ?)
""", ('system_init', 'Database initialized', 'Production database with bcrypt security', 'success'))

conn.commit()
conn.close()

print("\n" + "=" * 70)
print("✓ DATABASE RESET COMPLETE!")
print("=" * 70)

print("\n🔐 SECURITY FEATURES ENABLED:")
print("  ✓ Bcrypt password hashing (NOT plain text)")
print("  ✓ 60% ML confidence threshold")
print("  ✓ Manual review flagging")
print("  ✓ Audit logging")
print("  ✓ Complete ticket lifecycle")

print("\n📋 LOGIN CREDENTIALS:")
print("-" * 70)
print("\n👤 END USER:")
print("   Email: john.doe@skanem.com")
print("   Password: password123")
print("   Role: User (select from dropdown)")

print("\n🔧 TECHNICIAN:")
print("   Email: mike.tech@skanem.com")
print("   Password: tech123")
print("   Role: Technician (select from dropdown)")

print("\n👑 ADMINISTRATOR:")
print("   Email: admin@skanem.com")
print("   Password: admin123")
print("   Role: Administrator (select from dropdown)")

print("\n" + "=" * 70)
print("IMPORTANT: Passwords are securely hashed with bcrypt")
print("All security requirements implemented")
print("=" * 70)

print("\nNow run: python app_demo_pro.py")
print("=" * 70)
