-- Copy Trading Database Schema Extensions
-- This file extends the existing vanta_bot database with copy trading tables

-- New Tables for Copy Trading
CREATE TABLE trader_stats (
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
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(address, window)
);

CREATE INDEX idx_trader_stats_address_time ON trader_stats(address, last_trade_at);
CREATE INDEX idx_trader_stats_window ON trader_stats(window);

CREATE TABLE copytrader_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    is_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE copy_configurations (
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

CREATE TABLE leader_follows (
    id SERIAL PRIMARY KEY,
    copytrader_id INTEGER REFERENCES copytrader_profiles(id) ON DELETE CASCADE,
    leader_address VARCHAR(42) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    started_at TIMESTAMP DEFAULT NOW(),
    stopped_at TIMESTAMP,
    UNIQUE(copytrader_id, leader_address)
);

CREATE INDEX idx_leader_follows_address ON leader_follows(leader_address);
CREATE INDEX idx_leader_follows_active ON leader_follows(is_active);

CREATE TABLE copy_positions (
    id SERIAL PRIMARY KEY,
    copytrader_id INTEGER REFERENCES copytrader_profiles(id) ON DELETE CASCADE,
    leader_address VARCHAR(42),
    leader_trade_id VARCHAR(100),
    our_tx_hash VARCHAR(66),
    status VARCHAR(20) CHECK (status IN ('OPEN', 'CLOSED', 'FAILED', 'CANCELLED')),
    opened_at TIMESTAMP,
    closed_at TIMESTAMP,
    pnl_usd NUMERIC(20,2),
    executed_price NUMERIC(20,8),
    executed_size NUMERIC(20,8),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_copy_positions_copytrader ON copy_positions(copytrader_id, status);
CREATE INDEX idx_copy_positions_leader ON copy_positions(leader_address);
CREATE INDEX idx_copy_positions_status ON copy_positions(status);

CREATE TABLE trader_analytics (
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
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(address, window)
);

CREATE INDEX idx_trader_analytics_address ON trader_analytics(address);
CREATE INDEX idx_trader_analytics_archetype ON trader_analytics(archetype);
CREATE INDEX idx_trader_analytics_risk ON trader_analytics(risk_level);

-- Event monitoring tables
CREATE TABLE trade_events (
    id SERIAL PRIMARY KEY,
    address VARCHAR(42) NOT NULL,
    pair VARCHAR(20),
    is_long BOOLEAN,
    size NUMERIC(20,8),
    price NUMERIC(20,8),
    leverage INTEGER,
    event_type VARCHAR(10) CHECK (event_type IN ('OPENED', 'CLOSED')),
    block_number BIGINT,
    tx_hash VARCHAR(66),
    timestamp TIMESTAMP,
    fee NUMERIC(20,8),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trade_events_address ON trade_events(address);
CREATE INDEX idx_trade_events_timestamp ON trade_events(timestamp);
CREATE INDEX idx_trade_events_type ON trade_events(event_type);
CREATE INDEX idx_trade_events_pair ON trade_events(pair);

-- Performance monitoring
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC(20,4),
    metric_type VARCHAR(20) CHECK (metric_type IN ('counter', 'gauge', 'histogram')),
    labels JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_performance_metrics_name ON performance_metrics(metric_name);
CREATE INDEX idx_performance_metrics_timestamp ON performance_metrics(timestamp);

-- Health checks
CREATE TABLE health_checks (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) CHECK (status IN ('healthy', 'degraded', 'unhealthy')),
    details JSONB,
    checked_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_health_checks_service ON health_checks(service_name);
CREATE INDEX idx_health_checks_status ON health_checks(status);

-- Add some helpful views
CREATE VIEW active_copytraders AS
SELECT 
    cp.id,
    cp.user_id,
    cp.name,
    cp.is_enabled,
    COUNT(lf.id) as following_count,
    cp.created_at
FROM copytrader_profiles cp
LEFT JOIN leader_follows lf ON cp.id = lf.copytrader_id AND lf.is_active = true
WHERE cp.is_enabled = true
GROUP BY cp.id, cp.user_id, cp.name, cp.is_enabled, cp.created_at;

CREATE VIEW trader_performance_summary AS
SELECT 
    ts.address,
    ts.last_30d_volume_usd,
    ts.realized_pnl_clean_usd,
    ts.trade_count_30d,
    ts.win_rate,
    ta.archetype,
    ta.risk_level,
    ta.sharpe_like,
    ta.max_drawdown,
    (ts.realized_pnl_clean_usd / NULLIF(ts.last_30d_volume_usd, 0)) * 100 as roi_pct
FROM trader_stats ts
LEFT JOIN trader_analytics ta ON ts.address = ta.address AND ts.window = ta.window
WHERE ts.window = '30d'
ORDER BY ts.realized_pnl_clean_usd DESC;

-- Insert some initial configuration data
INSERT INTO performance_metrics (metric_name, metric_value, metric_type, labels) VALUES
('copy_trades_executed', 0, 'counter', '{"service": "copy_executor"}'),
('copy_trades_failed', 0, 'counter', '{"service": "copy_executor"}'),
('active_copytraders', 0, 'gauge', '{"service": "copy_executor"}'),
('leaders_monitored', 0, 'gauge', '{"service": "copy_executor"}'),
('ai_analyses_performed', 0, 'counter', '{"service": "trader_analyzer"}'),
('market_regime_changes', 0, 'counter', '{"service": "market_intelligence"}');

-- Add comments for documentation
COMMENT ON TABLE trader_stats IS 'Aggregated trader performance statistics with FIFO PnL calculation';
COMMENT ON TABLE copytrader_profiles IS 'User copytrader profiles with individual settings';
COMMENT ON TABLE copy_configurations IS 'Detailed copy trading configuration per profile';
COMMENT ON TABLE leader_follows IS 'Relationships between copytraders and leaders they follow';
COMMENT ON TABLE copy_positions IS 'Individual copy trades executed by the system';
COMMENT ON TABLE trader_analytics IS 'AI-generated trader analysis and classification';
COMMENT ON TABLE trade_events IS 'Raw blockchain events from Avantis Trading contract';
COMMENT ON TABLE performance_metrics IS 'System performance and operational metrics';
COMMENT ON TABLE health_checks IS 'Service health status monitoring';