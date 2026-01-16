-- ============================================================================
-- HELPDESK ML SYSTEM - COMPLETE DATABASE SCHEMA
-- Aligned with Project Requirements Document
-- Includes: Security, Scalability, Maintainability, Reliability
-- ============================================================================

-- ============================================================================
-- TABLE 1: USERS (End Users)
-- Purpose: Store end users who submit tickets
-- Security: Hashed passwords with bcrypt
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    department VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hashed password
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_department (department)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- TABLE 2: TECHNICIANS
-- Purpose: Store technicians who resolve tickets
-- Key Fields: skills, workload, availability
-- ============================================================================
CREATE TABLE IF NOT EXISTS technicians (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    skills TEXT,  -- Comma-separated: Hardware,Software,Network,Database
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hashed password
    current_workload INT DEFAULT 0,
    max_workload INT DEFAULT 10,
    availability_status ENUM('Available', 'Busy', 'Offline') DEFAULT 'Available',
    expertise_level ENUM('Junior', 'Mid', 'Senior') DEFAULT 'Mid',
    total_tickets_resolved INT DEFAULT 0,
    average_resolution_time DECIMAL(10,2) DEFAULT 0.00,  -- in hours
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_skills (skills(100)),
    INDEX idx_availability (availability_status),
    INDEX idx_workload (current_workload)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- TABLE 3: ADMINS
-- Purpose: System administrators/helpdesk managers
-- Privileges: Full system access, analytics, model management
-- ============================================================================
CREATE TABLE IF NOT EXISTS admins (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hashed password
    role VARCHAR(50) DEFAULT 'admin',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- TABLE 4: TICKETS (COMPLETE LIFECYCLE)
-- Status Flow: Submitted → Classified → Assigned → In Progress → Resolved → Closed
-- Key Addition: confidence_score, flagged_for_manual_review
-- ============================================================================
CREATE TABLE IF NOT EXISTS tickets (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50),  -- Hardware, Software, Network, Database
    priority ENUM('Low', 'Medium', 'High', 'Critical') DEFAULT 'Medium',
    status ENUM('Submitted', 'Classified', 'Assigned', 'In Progress', 'Resolved', 'Closed') DEFAULT 'Submitted',
    user_id INT NOT NULL,
    
    -- ML-SPECIFIC FIELDS (RELIABILITY REQUIREMENT)
    confidence_score DECIMAL(5,2) DEFAULT NULL,  -- 0.00 to 100.00
    flagged_for_manual_review BOOLEAN DEFAULT FALSE,
    manual_assignment_reason TEXT,  -- Why manual review was needed
    
    -- TIMESTAMPS (SLA TRACKING)
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    classified_at TIMESTAMP NULL,
    assigned_at TIMESTAMP NULL,
    in_progress_at TIMESTAMP NULL,
    resolved_at TIMESTAMP NULL,
    closed_at TIMESTAMP NULL,
    
    -- TIME TRACKING (PERFORMANCE ANALYSIS)
    time_to_classify INT DEFAULT NULL,  -- seconds
    time_to_assign INT DEFAULT NULL,    -- seconds
    time_to_resolve INT DEFAULT NULL,   -- seconds
    time_to_close INT DEFAULT NULL,     -- seconds
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    INDEX idx_ticket_number (ticket_number),
    INDEX idx_status (status),
    INDEX idx_category (category),
    INDEX idx_priority (priority),
    INDEX idx_user (user_id),
    INDEX idx_confidence (confidence_score),
    INDEX idx_flagged (flagged_for_manual_review),
    INDEX idx_submitted (submitted_at),
    INDEX idx_status_priority (status, priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- TABLE 5: ASSIGNMENTS (TRACEABILITY)
-- Purpose: Track which technician is assigned to which ticket
-- Key: Logs reassignments, tracks resolution time
-- ============================================================================
CREATE TABLE IF NOT EXISTS assignments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ticket_id INT NOT NULL,
    technician_id INT NOT NULL,
    assigned_by ENUM('System', 'Admin') DEFAULT 'System',  -- Auto vs Manual
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    notes TEXT,
    resolution_notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,  -- FALSE if reassigned
    
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
    FOREIGN KEY (technician_id) REFERENCES technicians(id) ON DELETE CASCADE,
    
    INDEX idx_ticket (ticket_id),
    INDEX idx_technician (technician_id),
    INDEX idx_active (is_active),
    INDEX idx_assigned_at (assigned_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- TABLE 6: NOTIFICATIONS (REAL-TIME TRACKING)
-- Purpose: Store notification history for audit and analytics
-- Socket.IO handles real-time delivery, this stores the record
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_type ENUM('user', 'technician', 'admin') NOT NULL,
    user_id INT NOT NULL,
    ticket_id INT,
    notification_type VARCHAR(50) NOT NULL,  -- ticket_assigned, status_updated, etc.
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP NULL,
    
    INDEX idx_user (user_type, user_id),
    INDEX idx_ticket (ticket_id),
    INDEX idx_is_read (is_read),
    INDEX idx_sent_at (sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- TABLE 7: MODEL_LOGS (MAINTAINABILITY REQUIREMENT)
-- Purpose: Track ML model versions, retraining, performance metrics
-- Critical for: Model lifecycle management, performance monitoring
-- ============================================================================
CREATE TABLE IF NOT EXISTS model_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    model_version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50) DEFAULT 'MultinomialNB',  -- Algorithm used
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- DATASET INFORMATION
    dataset_size INT NOT NULL,
    training_samples INT NOT NULL,
    testing_samples INT NOT NULL,
    
    -- PERFORMANCE METRICS
    accuracy DECIMAL(5,2) NOT NULL,           -- Overall accuracy %
    precision_avg DECIMAL(5,2),               -- Average precision
    recall_avg DECIMAL(5,2),                  -- Average recall
    f1_score_avg DECIMAL(5,2),                -- Average F1 score
    
    -- PER-CATEGORY METRICS (JSON)
    category_metrics JSON,  -- {Hardware: {precision, recall, f1}, ...}
    
    -- MODEL METADATA
    model_file_path VARCHAR(255),
    vectorizer_file_path VARCHAR(255),
    training_duration INT,  -- seconds
    trained_by VARCHAR(100) DEFAULT 'System',
    notes TEXT,
    
    is_active BOOLEAN DEFAULT TRUE,  -- Current production model
    deployed_at TIMESTAMP NULL,
    
    INDEX idx_version (model_version),
    INDEX idx_is_active (is_active),
    INDEX idx_training_date (training_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- TABLE 8: SYSTEM_LOGS (AUDIT TRAIL)
-- Purpose: Track system actions, login attempts, critical operations
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    log_type VARCHAR(50) NOT NULL,  -- login, ticket_submit, model_retrain, etc.
    user_type VARCHAR(20),
    user_id INT,
    action VARCHAR(255) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    status ENUM('success', 'failure', 'error') DEFAULT 'success',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_log_type (log_type),
    INDEX idx_user (user_type, user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- TABLE 9: SLA_RULES (SERVICE LEVEL AGREEMENTS)
-- Purpose: Define response time expectations per priority
-- ============================================================================
CREATE TABLE IF NOT EXISTS sla_rules (
    id INT PRIMARY KEY AUTO_INCREMENT,
    priority ENUM('Low', 'Medium', 'High', 'Critical') NOT NULL UNIQUE,
    response_time_minutes INT NOT NULL,  -- Time to first response
    resolution_time_hours INT NOT NULL,  -- Time to resolution
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- INSERT DEFAULT SLA RULES
-- ============================================================================
INSERT INTO sla_rules (priority, response_time_minutes, resolution_time_hours) VALUES
('Critical', 15, 4),
('High', 30, 8),
('Medium', 60, 24),
('Low', 120, 48)
ON DUPLICATE KEY UPDATE response_time_minutes=VALUES(response_time_minutes);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View: Active Tickets Summary
CREATE OR REPLACE VIEW v_active_tickets_summary AS
SELECT 
    status,
    priority,
    category,
    COUNT(*) as ticket_count,
    AVG(confidence_score) as avg_confidence,
    SUM(CASE WHEN flagged_for_manual_review = TRUE THEN 1 ELSE 0 END) as flagged_count
FROM tickets
WHERE status NOT IN ('Closed')
GROUP BY status, priority, category;

-- View: Technician Performance
CREATE OR REPLACE VIEW v_technician_performance AS
SELECT 
    t.id,
    t.name,
    t.email,
    t.skills,
    t.current_workload,
    t.total_tickets_resolved,
    t.average_resolution_time,
    COUNT(CASE WHEN a.is_active = TRUE THEN 1 END) as active_assignments,
    COUNT(CASE WHEN a.completed_at IS NOT NULL THEN 1 END) as completed_assignments,
    AVG(TIMESTAMPDIFF(HOUR, a.assigned_at, a.completed_at)) as avg_completion_hours
FROM technicians t
LEFT JOIN assignments a ON t.id = a.technician_id
GROUP BY t.id;

-- View: Model Performance History
CREATE OR REPLACE VIEW v_model_performance AS
SELECT 
    model_version,
    training_date,
    dataset_size,
    accuracy,
    precision_avg,
    recall_avg,
    f1_score_avg,
    is_active,
    deployed_at
FROM model_logs
ORDER BY training_date DESC;

-- ============================================================================
-- STORED PROCEDURES
-- ============================================================================

DELIMITER //

-- Procedure: Log Model Training
CREATE PROCEDURE sp_log_model_training(
    IN p_version VARCHAR(50),
    IN p_dataset_size INT,
    IN p_train_size INT,
    IN p_test_size INT,
    IN p_accuracy DECIMAL(5,2),
    IN p_model_path VARCHAR(255)
)
BEGIN
    -- Deactivate previous models
    UPDATE model_logs SET is_active = FALSE WHERE is_active = TRUE;
    
    -- Insert new model log
    INSERT INTO model_logs (
        model_version, dataset_size, training_samples, testing_samples,
        accuracy, model_file_path, is_active, deployed_at
    ) VALUES (
        p_version, p_dataset_size, p_train_size, p_test_size,
        p_accuracy, p_model_path, TRUE, NOW()
    );
END //

-- Procedure: Update Technician Workload
CREATE PROCEDURE sp_update_technician_workload(
    IN p_technician_id INT
)
BEGIN
    UPDATE technicians
    SET current_workload = (
        SELECT COUNT(*) 
        FROM assignments 
        WHERE technician_id = p_technician_id 
        AND is_active = TRUE
    )
    WHERE id = p_technician_id;
END //

-- Procedure: Close Ticket
CREATE PROCEDURE sp_close_ticket(
    IN p_ticket_id INT,
    IN p_closed_by VARCHAR(50)
)
BEGIN
    DECLARE v_submitted_at TIMESTAMP;
    
    SELECT submitted_at INTO v_submitted_at FROM tickets WHERE id = p_ticket_id;
    
    UPDATE tickets 
    SET 
        status = 'Closed',
        closed_at = NOW(),
        time_to_close = TIMESTAMPDIFF(SECOND, v_submitted_at, NOW())
    WHERE id = p_ticket_id;
    
    -- Log the action
    INSERT INTO system_logs (log_type, action, details)
    VALUES ('ticket_close', 'Ticket closed', CONCAT('Ticket #', p_ticket_id, ' closed by ', p_closed_by));
END //

DELIMITER ;

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMP TRACKING
-- ============================================================================

DELIMITER //

-- Trigger: Auto-update timestamps on status change
CREATE TRIGGER trg_ticket_status_timestamps
BEFORE UPDATE ON tickets
FOR EACH ROW
BEGIN
    IF NEW.status = 'Classified' AND OLD.status = 'Submitted' THEN
        SET NEW.classified_at = NOW();
        SET NEW.time_to_classify = TIMESTAMPDIFF(SECOND, OLD.submitted_at, NOW());
    END IF;
    
    IF NEW.status = 'Assigned' AND OLD.status != 'Assigned' THEN
        SET NEW.assigned_at = NOW();
        SET NEW.time_to_assign = TIMESTAMPDIFF(SECOND, OLD.submitted_at, NOW());
    END IF;
    
    IF NEW.status = 'In Progress' AND OLD.status != 'In Progress' THEN
        SET NEW.in_progress_at = NOW();
    END IF;
    
    IF NEW.status = 'Resolved' AND OLD.status != 'Resolved' THEN
        SET NEW.resolved_at = NOW();
        SET NEW.time_to_resolve = TIMESTAMPDIFF(SECOND, OLD.submitted_at, NOW());
    END IF;
    
    IF NEW.status = 'Closed' AND OLD.status != 'Closed' THEN
        SET NEW.closed_at = NOW();
        SET NEW.time_to_close = TIMESTAMPDIFF(SECOND, OLD.submitted_at, NOW());
    END IF;
END //

DELIMITER ;

-- ============================================================================
-- PERFORMANCE OPTIMIZATION INDEXES
-- Already added inline above, but listing here for reference:
-- ============================================================================
-- users: idx_email, idx_department
-- technicians: idx_email, idx_skills, idx_availability, idx_workload
-- admins: idx_email
-- tickets: idx_ticket_number, idx_status, idx_category, idx_priority, 
--          idx_user, idx_confidence, idx_flagged, idx_submitted, idx_status_priority
-- assignments: idx_ticket, idx_technician, idx_active, idx_assigned_at
-- notifications: idx_user, idx_ticket, idx_is_read, idx_sent_at
-- model_logs: idx_version, idx_is_active, idx_training_date
-- system_logs: idx_log_type, idx_user, idx_created_at, idx_status

-- ============================================================================
-- DATABASE SETUP COMPLETE
-- Next Steps: Run this schema, then update application code
-- ============================================================================
