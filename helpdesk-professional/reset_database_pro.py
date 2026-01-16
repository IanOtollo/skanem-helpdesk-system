#!/usr/bin/env python3
"""
Production Database Reset Script - With BCRYPT
"""

import os
import sqlite3
import bcrypt

DB_PATH = 'helpdesk.db'

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

print("=" * 70)
print("DATABASE RESET - PRODUCTION VERSION (BCRYPT)")
print("=" * 70)

if os.path.exists(DB_PATH):
    print(f"\n✓ Deleting old database...")
    os.remove(DB_PATH)

print("✓ Creating database with bcrypt security...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Tables
cursor.execute('''CREATE TABLE users (
    id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, phone TEXT,
    department TEXT, password_hash TEXT, role TEXT DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP
)''')

cursor.execute('''CREATE TABLE technicians (
    id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, phone TEXT, skills TEXT,
    password_hash TEXT, current_workload INTEGER DEFAULT 0, max_workload INTEGER DEFAULT 10,
    availability_status TEXT DEFAULT 'Available', expertise_level TEXT DEFAULT 'Mid',
    total_tickets_resolved INTEGER DEFAULT 0, average_resolution_time REAL DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP
)''')

cursor.execute('''CREATE TABLE admins (
    id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password_hash TEXT,
    role TEXT DEFAULT 'admin', is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP
)''')

cursor.execute('''CREATE TABLE tickets (
    id INTEGER PRIMARY KEY, ticket_number TEXT UNIQUE, subject TEXT, description TEXT,
    category TEXT, priority TEXT DEFAULT 'Medium', status TEXT DEFAULT 'Submitted',
    user_id INTEGER, confidence_score REAL, flagged_for_manual_review BOOLEAN DEFAULT FALSE,
    manual_assignment_reason TEXT, submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    classified_at TIMESTAMP, assigned_at TIMESTAMP, in_progress_at TIMESTAMP,
    resolved_at TIMESTAMP, closed_at TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
)''')

cursor.execute('''CREATE TABLE assignments (
    id INTEGER PRIMARY KEY, ticket_id INTEGER, technician_id INTEGER,
    assigned_by TEXT DEFAULT 'System', assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP, completed_at TIMESTAMP, notes TEXT, resolution_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id), FOREIGN KEY (technician_id) REFERENCES technicians(id)
)''')

cursor.execute('''CREATE TABLE notifications (
    id INTEGER PRIMARY KEY, user_type TEXT, user_id INTEGER, ticket_id INTEGER,
    notification_type TEXT, title TEXT, message TEXT, is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, read_at TIMESTAMP
)''')

cursor.execute('''CREATE TABLE model_logs (
    id INTEGER PRIMARY KEY, model_version TEXT, model_type TEXT DEFAULT 'LogisticRegression',
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, dataset_size INTEGER,
    training_samples INTEGER, testing_samples INTEGER, accuracy REAL,
    precision_avg REAL, recall_avg REAL, f1_score_avg REAL, category_metrics TEXT,
    model_file_path TEXT, vectorizer_file_path TEXT, training_duration INTEGER,
    trained_by TEXT DEFAULT 'System', notes TEXT, is_active BOOLEAN DEFAULT TRUE, deployed_at TIMESTAMP
)''')

cursor.execute('''CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY, log_type TEXT, user_type TEXT, user_id INTEGER,
    action TEXT, details TEXT, status TEXT DEFAULT 'success',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')

print("✓ Inserting demo data with BCRYPT-hashed passwords...")

# Users
for name, email, phone, dept, pw in [
    ('John Doe', 'john.doe@skanem.com', '+254712345678', 'Production', 'password123'),
    ('Jane Smith', 'jane.smith@skanem.com', '+254723456789', 'Quality Control', 'password123'),
    ('Bob Wilson', 'bob.wilson@skanem.com', '+254734567890', 'Logistics', 'password123')
]:
    cursor.execute("INSERT INTO users (name, email, phone, department, password_hash) VALUES (?, ?, ?, ?, ?)",
                  (name, email, phone, dept, hash_password(pw)))

# Technicians
for name, email, phone, skills, pw in [
    ('Mike Johnson', 'mike.tech@skanem.com', '+254745678901', 'Hardware,Network', 'tech123'),
    ('Sarah Davis', 'sarah.tech@skanem.com', '+254756789012', 'Software,Database', 'tech123'),
    ('James Brown', 'james.tech@skanem.com', '+254767890123', 'Hardware,Software,Network', 'tech123')
]:
    cursor.execute("INSERT INTO technicians (name, email, phone, skills, password_hash) VALUES (?, ?, ?, ?, ?)",
                  (name, email, phone, skills, hash_password(pw)))

# Admin
cursor.execute("INSERT INTO admins (name, email, password_hash) VALUES (?, ?, ?)",
              ('System Admin', 'admin@skanem.com', hash_password('admin123')))

conn.commit()
conn.close()

print("\n" + "=" * 70)
print("✓ COMPLETE! All passwords are BCRYPT-hashed")
print("=" * 70)
print("\n📋 LOGIN CREDENTIALS:")
print("\n👤 USER: john.doe@skanem.com / password123")
print("🔧 TECH: mike.tech@skanem.com / tech123")
print("👑 ADMIN: admin@skanem.com / admin123")
print("\n▶ Run: python app_demo_pro.py")
print("=" * 70 + "\n")
