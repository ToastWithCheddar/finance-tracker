-- Initial database setup
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create database if it doesn't exist
DO $ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'finance_tracker') THEN
        CREATE DATABASE finance_tracker;
    END IF;
END $;

-- Set timezone
SET timezone = 'UTC';

-- Create custom functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

-- Create function to calculate budget usage
CREATE OR REPLACE FUNCTION calculate_budget_usage(
    p_budget_id UUID,
    p_start_date DATE,
    p_end_date DATE
) RETURNS DECIMAL AS $
DECLARE
    total_spent DECIMAL := 0;
BEGIN
    SELECT COALESCE(SUM(amount_cents), 0) / 100.0
    INTO total_spent
    FROM transactions t
    JOIN budgets b ON t.category_id = b.category_id
    WHERE b.id = p_budget_id
    AND t.transaction_date >= p_start_date
    AND t.transaction_date <= p_end_date;
    
    RETURN total_spent;
END;
$ LANGUAGE plpgsql;

-- Create function to get spending by category
CREATE OR REPLACE FUNCTION get_spending_by_category(
    p_user_id UUID,
    p_start_date DATE,
    p_end_date DATE
) RETURNS TABLE(
    category_name VARCHAR,
    total_amount_cents BIGINT,
    transaction_count INTEGER
) AS $
BEGIN
    RETURN QUERY
    SELECT 
        c.name,
        COALESCE(SUM(t.amount_cents), 0),
        COUNT(t.id)::INTEGER
    FROM categories c
    LEFT JOIN transactions t ON c.id = t.category_id
    WHERE (c.user_id = p_user_id OR c.is_system = true)
    AND (t.user_id = p_user_id OR t.id IS NULL)
    AND (t.transaction_date >= p_start_date OR t.id IS NULL)
    AND (t.transaction_date <= p_end_date OR t.id IS NULL)
    GROUP BY c.id, c.name
    ORDER BY SUM(t.amount_cents) DESC NULLS LAST;
END;
$ LANGUAGE plpgsql;

-- Create trigger for budget alerts
CREATE OR REPLACE FUNCTION notify_budget_alert()
RETURNS TRIGGER AS $
DECLARE
    budget_usage DECIMAL;
    budget_limit DECIMAL;
    alert_threshold DECIMAL;
    budget_id UUID;
BEGIN
    -- Get budget information
    SELECT b.id, b.amount_cents / 100.0, b.alert_threshold
    INTO budget_id, budget_limit, alert_threshold
    FROM budgets b
    WHERE b.category_id = NEW.category_id
    AND b.user_id = NEW.user_id
    AND b.is_active = true
    AND NEW.transaction_date >= b.start_date
    AND (b.end_date IS NULL OR NEW.transaction_date <= b.end_date)
    LIMIT 1;
    
    IF budget_id IS NOT NULL THEN
        -- Calculate current usage
        SELECT calculate_budget_usage(
            budget_id,
            date_trunc('month', NEW.transaction_date)::DATE,
            (date_trunc('month', NEW.transaction_date) + INTERVAL '1 month - 1 day')::DATE
        ) INTO budget_usage;
        
        -- Check if alert threshold is exceeded
        IF budget_usage >= (budget_limit * alert_threshold) THEN
            INSERT INTO insights (user_id, type, title, description, priority, metadata)
            VALUES (
                NEW.user_id,
                'budget_alert',
                'Budget Alert: Spending Limit Approaching',
                format('You have spent $%.2f of your $%.2f budget (%.1f%%)', 
                       budget_usage, budget_limit, (budget_usage / budget_limit * 100)),
                1,
                json_build_object(
                    'category_id', NEW.category_id,
                    'budget_id', budget_id,
                    'budget_usage', budget_usage,
                    'budget_limit', budget_limit,
                    'percentage', budget_usage / budget_limit * 100
                )
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

-- Performance optimizations
SET shared_preload_libraries = 'pg_stat_statements';
SET log_statement = 'all';
SET log_min_duration_statement = 1000;