#!/usr/bin/env python3
"""
Database Reset Script
Deletes old database and creates fresh one with correct credentials
"""

import os
import sqlite3

# Database path
DB_PATH = 'helpdesk.db'

print("=" * 60)
print("DATABASE RESET SCRIPT")
print("=" * 60)

# Delete old database if exists
if os.path.exists(DB_PATH):
    print(f"\n[1/3] Deleting old database: {DB_PATH}")
    os.remove(DB_PATH)
    print("✓ Old database deleted")
else:
    print(f"\n[1/3] No existing database found")

# Create new database
print("\n[2/3] Creating fresh database...")
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Create tables
print("  - Creating users table...")
cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        department TEXT,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        password TEXT NOT NULL,
        current_workload INTEGER DEFAULT 0,
        availability_status TEXT DEFAULT 'Available',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

print("  - Creating tickets table...")
cursor.execute('''
    CREATE TABLE tickets (
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

print("  - Creating assignments table...")
cursor.execute('''
    CREATE TABLE assignments (
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

print("  - Creating admins table...")
cursor.execute('''
    CREATE TABLE admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Insert demo data
print("\n[3/3] Inserting demo data...")

print("  - Adding users...")
cursor.execute("""
    INSERT INTO users (name, email, phone, department, password) VALUES
    ('John Doe', 'john.doe@skanem.com', '+254712345678', 'Production', 'password123'),
    ('Jane Smith', 'jane.smith@skanem.com', '+254723456789', 'Quality Control', 'password123'),
    ('Bob Wilson', 'bob.wilson@skanem.com', '+254734567890', 'Logistics', 'password123')
""")

print("  - Adding technicians...")
cursor.execute("""
    INSERT INTO technicians (name, email, phone, skills, password) VALUES
    ('Mike Johnson', 'mike.tech@skanem.com', '+254745678901', 'Hardware,Network', 'tech123'),
    ('Sarah Davis', 'sarah.tech@skanem.com', '+254756789012', 'Software,Database', 'tech123'),
    ('James Brown', 'james.tech@skanem.com', '+254767890123', 'Hardware,Software,Network', 'tech123')
""")

print("  - Adding admin...")
cursor.execute("""
    INSERT INTO admins (name, email, password) VALUES
    ('System Admin', 'admin@skanem.com', 'admin123')
""")

conn.commit()
conn.close()

print("\n" + "=" * 60)
print("✓ DATABASE RESET COMPLETE!")
print("=" * 60)

print("\n📋 LOGIN CREDENTIALS:")
print("-" * 60)
print("\n👤 USER:")
print("   Email: john.doe@skanem.com")
print("   Password: password123")
print("   Role: User")

print("\n🔧 TECHNICIAN:")
print("   Email: mike.tech@skanem.com")
print("   Password: tech123")
print("   Role: Technician")

print("\n👑 ADMIN:")
print("   Email: admin@skanem.com")
print("   Password: admin123")
print("   Role: Administrator")

print("\n" + "=" * 60)
print("Now run: python app_demo.py")
print("=" * 60)
