$env:PGPASSWORD = "Your-Password-Here"

# Create database
psql -U postgres -h localhost -c "DROP DATABASE IF EXISTS cheating_detection;"
psql -U postgres -h localhost -c "CREATE DATABASE cheating_detection;"

# Create tables
$createTables = @"
CREATE TABLE IF NOT EXISTS detections (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    behavior_type VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    frame_path VARCHAR(255) NOT NULL,
    details TEXT,
    bbox JSON
);

CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_detections_behavior_type ON detections(behavior_type);
"@

psql -U postgres -h localhost -d cheating_detection -c $createTables

Write-Host "Database initialized successfully"
