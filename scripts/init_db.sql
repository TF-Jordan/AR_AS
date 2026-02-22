-- ==============================================================================
-- AR_AS RaaS Platform - Database Initialization
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Comments table (for sentiment analysis)
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    product_type VARCHAR(50) NOT NULL,
    commentaire TEXT NOT NULL,
    sentiment_score FLOAT,
    sentiment_label VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comments_product ON comments(product_id, product_type);
CREATE INDEX IF NOT EXISTS idx_comments_client ON comments(client_id);

-- Timestamp update function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';
