-- Copy Trading Database Schema Extension
-- This file extends the existing Vanta Bot database with copy trading functionality

-- Trader Statistics Table
-- Stores 30-day rolling statistics for all traders on Avantis
CREATE TABLE IF NOT EXISTS trader_stats (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) NOT NULL,
    window VARCHAR(10) DEFAULT '30d',
    last_30d_volume_usd NUMERIC(20,2),
    median_trade_size_usd NUMERIC(20,2),
    trade_count_30d INTEGER,
    realized_pnl_clean_usd NUMERIC(20,2),
    last_trade_at TIMESTAMP,
    maker_ratio NUMERIC(5,4),
    unique_symbols INTEGER,
    win_rate NUMERIC(5,4),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(address, window)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_trader_stats_address ON trader_stats(address);
CREATE INDEX IF NOT EXISTS idx_trader_stats_last_trade ON trader_stats(last_trade_at);
CREATE INDEX IF NOT EXISTS idx_trader_stats_volume ON trader_stats(last_30d_volume_usd DESC);
CREATE INDEX IF NOT EXISTS idx_trader_stats_pnl ON trader_stats(realized_pnl_clean_usd DESC);

-- Copy Trader Profiles Table
-- User profiles for copy trading functionality
CREATE TABLE IF NOT EXISTS copytrader_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    is_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Copy Trading Configurations Table
-- Detailed configuration for each copytrader profile
CREATE TABLE IF NOT EXISTS copy_configurations (
    id SERIAL PRIMARY KEY,
    copytrader_id INTEGER REFERENCES copytrader_profiles(id) ON DELETE CASCADE,
    sizing_mode VARCHAR(20) CHECK (sizing_mode IN ('FIXED_NOTIONAL', 'PCT_EQUITY')),
    sizing_value NUMERIC(10,4),
    max_slippage_bps INTEGER DEFAULT 100,
    max_leverage NUMERIC(6,2) DEFAULT 50,
    notional_cap NUMERIC(20,2),
    tp_sl_policy JSONB,
    pair_filters JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Leader Follows Table
-- Tracks which traders each copytrader is following
CREATE TABLE IF NOT EXISTS leader_follows (
    id SERIAL PRIMARY KEY,
    copytrader_id INTEGER REFERENCES copytrader_profiles(id) ON DELETE CASCADE,
    leader_address VARCHAR(42) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    started_at TIMESTAMP DEFAULT NOW(),
    stopped_at TIMESTAMP,
    UNIQUE(copytrader_id, leader_address)
);

-- Create indexes for leader follows
CREATE INDEX IF NOT EXISTS idx_leader_follows_address ON leader_follows(leader_address);
CREATE INDEX IF NOT EXISTS idx_leader_follows_active ON leader_follows(is_active);

-- Copy Positions Table
-- Tracks all copy trades executed
CREATE TABLE IF NOT EXISTS copy_positions (
    id SERIAL PRIMARY KEY,
    copytrader_id INTEGER REFERENCES copytrader_profiles(id) ON DELETE CASCADE,
    leader_address VARCHAR(42),
    leader_trade_id VARCHAR(100),
    our_tx_hash VARCHAR(66),
    status VARCHAR(20) CHECK (status IN ('OPEN', 'CLOSED', 'FAILED', 'CANCELLED')),
    opened_at TIMESTAMP,
    closed_at TIMESTAMP,
    executed_price NUMERIC(20,8),
    executed_size NUMERIC(20,8),
    pnl_usd NUMERIC(20,2),
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for copy positions
CREATE INDEX IF NOT EXISTS idx_copy_positions_copytrader ON copy_positions(copytrader_id);
CREATE INDEX IF NOT EXISTS idx_copy_positions_status ON copy_positions(status);
CREATE INDEX IF NOT EXISTS idx_copy_positions_leader ON copy_positions(leader_address);
CREATE INDEX IF NOT EXISTS idx_copy_positions_opened ON copy_positions(opened_at);

-- Trader Analytics Table
-- AI-generated analytics and predictions for traders
CREATE TABLE IF NOT EXISTS trader_analytics (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) NOT NULL,
    window VARCHAR(10) DEFAULT '30d',
    sharpe_like NUMERIC(8,4),
    max_drawdown NUMERIC(6,4),
    consistency NUMERIC(6,4),
    archetype VARCHAR(50),
    win_prob_7d NUMERIC(6,4),
    expected_dd_7d NUMERIC(6,4),
    optimal_copy_ratio NUMERIC(6,4),
    risk_level VARCHAR(10) CHECK (risk_level IN ('LOW', 'MED', 'HIGH')),
    strengths JSONB,
    warnings JSONB,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(address, window)
);

-- Create indexes for trader analytics
CREATE INDEX IF NOT EXISTS idx_trader_analytics_address ON trader_analytics(address);
CREATE INDEX IF NOT EXISTS idx_trader_analytics_archetype ON trader_analytics(archetype);
CREATE INDEX IF NOT EXISTS idx_trader_analytics_risk ON trader_analytics(risk_level);

-- Raw Trade Events Table
-- Stores all trade events from blockchain for analysis
CREATE TABLE IF NOT EXISTS trade_events (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) NOT NULL,
    pair_index INTEGER,
    pair_symbol VARCHAR(20),
    is_long BOOLEAN,
    size NUMERIC(20,8),
    price NUMERIC(20,8),
    leverage NUMERIC(6,2),
    event_type VARCHAR(10) CHECK (event_type IN ('OPENED', 'CLOSED')),
    block_number BIGINT,
    tx_hash VARCHAR(66),
    timestamp TIMESTAMP,
    fee NUMERIC(20,8),
    trade_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for trade events
CREATE INDEX IF NOT EXISTS idx_trade_events_address ON trade_events(address);
CREATE INDEX IF NOT EXISTS idx_trade_events_timestamp ON trade_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_trade_events_type ON trade_events(event_type);
CREATE INDEX IF NOT EXISTS idx_trade_events_pair ON trade_events(pair_symbol);

-- Market Regime Data Table
-- Stores market condition analysis for copy timing
CREATE TABLE IF NOT EXISTS market_regime_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    volatility NUMERIC(8,6),
    trend VARCHAR(10),
    regime_color VARCHAR(10) CHECK (regime_color IN ('green', 'yellow', 'red')),
    confidence NUMERIC(4,3),
    price_data JSONB,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(symbol)
);

-- Create indexes for market regime
CREATE INDEX IF NOT EXISTS idx_market_regime_symbol ON market_regime_data(symbol);
CREATE INDEX IF NOT EXISTS idx_market_regime_color ON market_regime_data(regime_color);

-- Copy Performance Attribution Table
-- Tracks performance attribution between manual and copy trading
CREATE TABLE IF NOT EXISTS copy_performance_attribution (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    manual_pnl_usd NUMERIC(20,2) DEFAULT 0,
    copy_pnl_usd NUMERIC(20,2) DEFAULT 0,
    total_pnl_usd NUMERIC(20,2) DEFAULT 0,
    copy_attribution_pct NUMERIC(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Create indexes for performance attribution
CREATE INDEX IF NOT EXISTS idx_copy_perf_user ON copy_performance_attribution(user_id);
CREATE INDEX IF NOT EXISTS idx_copy_perf_date ON copy_performance_attribution(date);

-- AI Model Metadata Table
-- Stores metadata about AI models and their performance
CREATE TABLE IF NOT EXISTS ai_model_metadata (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    model_version VARCHAR(20),
    training_data_size INTEGER,
    accuracy_score NUMERIC(5,4),
    last_trained_at TIMESTAMP,
    model_parameters JSONB,
    performance_metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for AI model metadata
CREATE INDEX IF NOT EXISTS idx_ai_model_name ON ai_model_metadata(model_name);
CREATE INDEX IF NOT EXISTS idx_ai_model_version ON ai_model_metadata(model_version);

-- Insert default AI model metadata
INSERT INTO ai_model_metadata (model_name, model_version, training_data_size, accuracy_score, last_trained_at, model_parameters, performance_metrics) 
VALUES (
    'trader_analyzer_v1',
    '1.0.0',
    0,
    0.0,
    NOW(),
    '{"n_estimators": 100, "random_state": 42}',
    '{"precision": 0.0, "recall": 0.0, "f1_score": 0.0}'
) ON CONFLICT DO NOTHING;

-- Create views for easier querying

-- Top Traders View
CREATE OR REPLACE VIEW top_traders_view AS
SELECT 
    ts.address,
    ts.last_30d_volume_usd,
    ts.realized_pnl_clean_usd,
    ts.trade_count_30d,
    ts.win_rate,
    ts.last_trade_at,
    ta.archetype,
    ta.risk_level,
    ta.sharpe_like,
    ta.consistency,
    ta.copyability_score,
    ROW_NUMBER() OVER (ORDER BY ts.last_30d_volume_usd DESC) as volume_rank,
    ROW_NUMBER() OVER (ORDER BY ts.realized_pnl_clean_usd DESC) as pnl_rank
FROM trader_stats ts
LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
WHERE ts.last_trade_at > NOW() - INTERVAL '72 hours'
  AND ts.trade_count_30d >= 50
  AND ts.last_30d_volume_usd >= 100000
ORDER BY ts.last_30d_volume_usd DESC;

-- Active Copy Traders View
CREATE OR REPLACE VIEW active_copytraders_view AS
SELECT 
    cp.id as copytrader_id,
    cp.user_id,
    cp.name,
    cp.is_enabled,
    cc.sizing_mode,
    cc.sizing_value,
    cc.max_leverage,
    cc.max_slippage_bps,
    lf.leader_address,
    lf.started_at as follow_started_at,
    COUNT(cpos.id) as total_copy_trades,
    SUM(CASE WHEN cpos.status = 'CLOSED' THEN cpos.pnl_usd ELSE 0 END) as total_copy_pnl
FROM copytrader_profiles cp
LEFT JOIN copy_configurations cc ON cp.id = cc.copytrader_id
LEFT JOIN leader_follows lf ON cp.id = lf.copytrader_id AND lf.is_active = true
LEFT JOIN copy_positions cpos ON cp.id = cpos.copytrader_id
WHERE cp.is_enabled = true
GROUP BY cp.id, cp.user_id, cp.name, cp.is_enabled, cc.sizing_mode, cc.sizing_value, cc.max_leverage, cc.max_slippage_bps, lf.leader_address, lf.started_at;

-- Performance Summary View
CREATE OR REPLACE VIEW copy_performance_summary AS
SELECT 
    u.id as user_id,
    u.username,
    COUNT(DISTINCT cp.id) as total_copytraders,
    COUNT(DISTINCT lf.leader_address) as total_leaders_followed,
    COUNT(cpos.id) as total_copy_trades,
    SUM(CASE WHEN cpos.status = 'CLOSED' THEN cpos.pnl_usd ELSE 0 END) as total_copy_pnl,
    AVG(CASE WHEN cpos.status = 'CLOSED' THEN cpos.pnl_usd ELSE NULL END) as avg_copy_pnl,
    MAX(cpos.opened_at) as last_copy_trade_at
FROM users u
LEFT JOIN copytrader_profiles cp ON u.id = cp.user_id
LEFT JOIN leader_follows lf ON cp.id = lf.copytrader_id AND lf.is_active = true
LEFT JOIN copy_positions cpos ON cp.id = cpos.copytrader_id
GROUP BY u.id, u.username;

-- Add comments for documentation
COMMENT ON TABLE trader_stats IS '30-day rolling statistics for all traders on Avantis Protocol';
COMMENT ON TABLE copytrader_profiles IS 'User profiles for copy trading functionality';
COMMENT ON TABLE copy_configurations IS 'Detailed configuration for each copytrader profile';
COMMENT ON TABLE leader_follows IS 'Tracks which traders each copytrader is following';
COMMENT ON TABLE copy_positions IS 'Tracks all copy trades executed';
COMMENT ON TABLE trader_analytics IS 'AI-generated analytics and predictions for traders';
COMMENT ON TABLE trade_events IS 'Raw trade events from blockchain for analysis';
COMMENT ON TABLE market_regime_data IS 'Market condition analysis for copy timing';
COMMENT ON TABLE copy_performance_attribution IS 'Performance attribution between manual and copy trading';
COMMENT ON TABLE ai_model_metadata IS 'Metadata about AI models and their performance';

-- Grant permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bot_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bot_user;
