-- Helpdesk ML System Database Schema
-- Drop existing database if exists
DROP DATABASE IF EXISTS helpdesk_ml_system;
CREATE DATABASE helpdesk_ml_system;
USE helpdesk_ml_system;

-- Users table (for ticket submitters)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    department VARCHAR(50),
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Technicians table
CREATE TABLE technicians (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    skills TEXT, -- Comma-separated skills (Hardware,Software,Network)
    current_workload INT DEFAULT 0,
    availability_status ENUM('Available', 'Busy', 'Offline') DEFAULT 'Available',
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tickets table
CREATE TABLE tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_number VARCHAR(20) UNIQUE NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50), -- Auto-classified by ML (Hardware, Software, Network, Database)
    priority ENUM('Low', 'Medium', 'High', 'Critical') DEFAULT 'Medium',
    status ENUM('Open', 'Assigned', 'In Progress', 'Resolved', 'Closed') DEFAULT 'Open',
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Assignments table (tracks ticket assignments to technicians)
CREATE TABLE assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    technician_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    notes TEXT,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES technicians(id) ON DELETE CASCADE
);

-- Admin table
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data for testing

-- Sample users
INSERT INTO users (name, email, phone, department, password) VALUES
('John Doe', 'john.doe@skanem.com', '+254712345678', 'Production', 'password123'),
('Jane Smith', 'jane.smith@skanem.com', '+254723456789', 'Quality Control', 'password123'),
('Bob Wilson', 'bob.wilson@skanem.com', '+254734567890', 'Logistics', 'password123');

-- Sample technicians
INSERT INTO technicians (name, email, phone, skills, password) VALUES
('Tech Mike', 'mike.tech@skanem.com', '+254745678901', 'Hardware,Network', 'tech123'),
('Tech Sarah', 'sarah.tech@skanem.com', '+254756789012', 'Software,Database', 'tech123'),
('Tech James', 'james.tech@skanem.com', '+254767890123', 'Hardware,Software,Network', 'tech123');

-- Sample admin
INSERT INTO admins (name, email, password) VALUES
('Admin User', 'admin@skanem.com', 'admin123');

-- Sample tickets for testing
INSERT INTO tickets (ticket_number, subject, description, category, priority, user_id, status) VALUES
('TKT-001', 'Printer not working', 'The office printer on floor 2 is not responding', 'Hardware', 'Medium', 1, 'Open'),
('TKT-002', 'Email access issues', 'Cannot access my email account since this morning', 'Software', 'High', 2, 'Open'),
('TKT-003', 'Internet connection down', 'No internet connection in production area', 'Network', 'Critical', 3, 'Open');
