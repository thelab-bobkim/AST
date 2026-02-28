-- PostgreSQL 초기화 스크립트
CREATE TABLE IF NOT EXISTS trading_snapshots (
    id              SERIAL PRIMARY KEY,
    timestamp       VARCHAR(50),
    portfolio_value FLOAT DEFAULT 0,
    cash            FLOAT DEFAULT 0,
    position_value  FLOAT DEFAULT 0,
    total_pnl       FLOAT DEFAULT 0,
    total_pnl_pct   FLOAT DEFAULT 0,
    daily_pnl       FLOAT DEFAULT 0,
    position_count  INTEGER DEFAULT 0,
    win_rate        FLOAT DEFAULT 0,
    mode            VARCHAR(10) DEFAULT 'mock',
    holdings_json   TEXT DEFAULT '[]',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trade_records (
    id              SERIAL PRIMARY KEY,
    timestamp       VARCHAR(50),
    trade_type      VARCHAR(10),
    code            VARCHAR(10),
    name            VARCHAR(50),
    quantity        INTEGER DEFAULT 0,
    price           FLOAT DEFAULT 0,
    amount          FLOAT DEFAULT 0,
    pnl             FLOAT DEFAULT 0,
    reason          VARCHAR(100),
    portfolio_value FLOAT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON trading_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp    ON trade_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_code         ON trade_records(code);
