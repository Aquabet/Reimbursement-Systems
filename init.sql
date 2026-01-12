-- Initialize database for reimbursement system
-- This script runs when MySQL container starts

-- Create database (if it doesn't exist)
CREATE DATABASE IF NOT EXISTS reimbursement_db;

-- Use the database
USE reimbursement_db;

-- Verify tables will be created by Flask-Migrate
SELECT 'Database initialized. Tables will be created by Flask-Migrate on first run.' as status;
