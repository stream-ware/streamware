#!/bin/bash
# Streaming Tests for Streamware

set -e

echo "=========================================="
echo "STREAMWARE STREAMING TESTS"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Test 1: Kafka Produce
echo "=== Test 1: Kafka Produce ==="
info "Producing messages to Kafka"

# Create topic
docker-compose exec -T kafka kafka-topics \
    --create --if-not-exists \
    --topic test-events \
    --bootstrap-server localhost:9092 \
    --partitions 1 \
    --replication-factor 1 2>/dev/null || true

# Produce messages
for i in {1..5}; do
    echo "{\"id\":$i,\"message\":\"Test event $i\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" | \
        streamware "kafka://produce?topic=test-events" --data @- 2>/dev/null
done

success "Produced 5 messages to Kafka"
echo ""

# Test 2: Kafka Consume
echo "=== Test 2: Kafka Consume ==="
info "Consuming messages from Kafka (first 3)"

# Consume and limit output
timeout 5s streamware "kafka://consume?topic=test-events&group=test-consumer" \
    --pipe "transform://json" 2>/dev/null | head -3 || true

success "Consumed messages from Kafka"
echo ""

# Test 3: PostgreSQL Stream Changes
echo "=== Test 3: PostgreSQL Data Stream ==="
info "Streaming data from PostgreSQL"

# Insert test events
sq postgres "INSERT INTO events (event_type, data) VALUES 
    ('test_event', '{\"value\": 1}'),
    ('test_event', '{\"value\": 2}'),
    ('test_event', '{\"value\": 3}')" 2>/dev/null || true

# Query events
sq postgres "SELECT * FROM events ORDER BY created_at DESC LIMIT 5" --json

success "PostgreSQL streaming test completed"
echo ""

# Test 4: Real-time Pipeline
echo "=== Test 4: Real-time Pipeline Test ==="
info "Testing real-time data pipeline"

# Create a producer script
cat > /tmp/producer.sh << 'EOF'
#!/bin/bash
for i in {1..3}; do
    echo "{\"seq\":$i,\"value\":$RANDOM,\"time\":\"$(date +%s)\"}" | \
        streamware "kafka://produce?topic=metrics" --data @- 2>/dev/null
    sleep 0.5
done
EOF
chmod +x /tmp/producer.sh

# Start producer in background
/tmp/producer.sh &
PRODUCER_PID=$!

# Consume for a bit
timeout 3s streamware "kafka://consume?topic=metrics&group=processor" \
    --pipe "transform://json" 2>/dev/null | head -3 || true

# Wait for producer
wait $PRODUCER_PID 2>/dev/null || true

success "Real-time pipeline test completed"
echo ""

# Test 5: HTTP Stream
echo "=== Test 5: HTTP Streaming ==="
info "Testing HTTP stream processing"

# Simulate multiple requests
for i in {1..3}; do
    sq get mock-api:8080/data --json > /tmp/stream_$i.json &
done
wait

success "HTTP streaming completed"
echo ""

# Summary
echo "=========================================="
echo "STREAMING TEST SUMMARY"
echo "=========================================="
echo ""
success "All streaming tests completed!"
echo ""
echo "Kafka topics:"
docker-compose exec -T kafka kafka-topics \
    --list --bootstrap-server localhost:9092 2>/dev/null | grep -E "test-|metrics" || echo "  (topics may not be visible yet)"
echo ""
echo "Try manual streaming:"
echo "  # Producer (Terminal 1):"
echo "  while true; do"
echo "    echo '{\"time\":\"\$(date)\",\"value\":\$RANDOM}' | \\"
echo "      streamware 'kafka://produce?topic=live' --data @-"
echo "    sleep 1"
echo "  done"
echo ""
echo "  # Consumer (Terminal 2):"
echo "  streamware 'kafka://consume?topic=live&group=viewer' --stream"
echo ""
