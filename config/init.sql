-- Database initialization for Vanta Bot
-- This script sets up the database with proper permissions

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE vanta_bot'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'vanta_bot')\gexec

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE vanta_bot TO bot_user;
