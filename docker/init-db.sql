-- Streamware PostgreSQL initialization script

-- Create tables for testing
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    age INTEGER,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2),
    category VARCHAR(50),
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending',
    order_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),
    data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20),
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO users (name, email, age, active) VALUES
    ('Alice Johnson', 'alice@example.com', 30, true),
    ('Bob Smith', 'bob@example.com', 25, true),
    ('Charlie Brown', 'charlie@example.com', 35, false),
    ('Diana Prince', 'diana@example.com', 28, true),
    ('Eve Wilson', 'eve@example.com', 22, true);

INSERT INTO products (name, price, category, stock) VALUES
    ('Laptop Pro', 1299.99, 'Electronics', 50),
    ('Wireless Mouse', 29.99, 'Electronics', 200),
    ('Coffee Maker', 89.99, 'Appliances', 75),
    ('Desk Chair', 199.99, 'Furniture', 30),
    ('Notebook Set', 15.99, 'Stationery', 500);

INSERT INTO orders (user_id, product_id, quantity, status, order_date) VALUES
    (1, 1, 1, 'completed', '2024-01-15'),
    (2, 2, 2, 'completed', '2024-01-16'),
    (1, 3, 1, 'pending', '2024-01-17'),
    (3, 4, 1, 'shipped', '2024-01-18'),
    (4, 5, 3, 'completed', '2024-01-19');

INSERT INTO events (event_type, data) VALUES
    ('user_login', '{"user_id": 1, "ip": "192.168.1.1"}'),
    ('product_view', '{"product_id": 1, "user_id": 2}'),
    ('order_placed', '{"order_id": 1, "total": 1299.99}'),
    ('user_logout', '{"user_id": 1, "session_duration": 3600}');

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(active);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_created ON events(created_at);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO streamware;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO streamware;
