#!/bin/bash
# Basic Streamware Tests in Docker

set -e

echo "=========================================="
echo "STREAMWARE BASIC TESTS"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

info() {
    echo -e "${BLUE}→ $1${NC}"
}

# Test 1: Mock API Connection
echo "=== Test 1: Mock API Connection ==="
info "Testing mock-api:8080/health"
if sq get mock-api:8080/health --json > /dev/null 2>&1; then
    success "Mock API is responding"
else
    error "Mock API connection failed"
    exit 1
fi
echo ""

# Test 2: Get Users
echo "=== Test 2: Get Users ==="
info "Fetching users from mock API"
sq get mock-api:8080/users --json --save /tmp/users.json
if [ -f /tmp/users.json ]; then
    USER_COUNT=$(cat /tmp/users.json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
    success "Retrieved $USER_COUNT users"
else
    error "Failed to fetch users"
    exit 1
fi
echo ""

# Test 3: JSON to CSV
echo "=== Test 3: JSON to CSV Transformation ==="
info "Converting users to CSV"
sq file /tmp/users.json --json --csv --save /tmp/users.csv
if [ -f /tmp/users.csv ]; then
    success "CSV file created"
    head -3 /tmp/users.csv
else
    error "CSV conversion failed"
fi
echo ""

# Test 4: PostgreSQL Query
echo "=== Test 4: PostgreSQL Query ==="
info "Querying PostgreSQL database"
if sq postgres "SELECT COUNT(*) as user_count FROM users" --json 2>/dev/null; then
    success "PostgreSQL query executed"
else
    error "PostgreSQL query failed (database may not be ready)"
fi
echo ""

# Test 5: Python DSL
echo "=== Test 5: Python DSL Test ==="
info "Testing Python DSL"
python3 << 'EOF'
from streamware import Pipeline, quick

# Test Fluent API
result = (
    Pipeline()
    .http_get("http://mock-api:8080/health")
    .to_json()
    .run()
)
print(f"✓ Fluent API: {result['status']}")

# Test Quick API
result = quick("http://mock-api:8080/data").json().run()
print(f"✓ Quick API: {result['status']}")
EOF

if [ $? -eq 0 ]; then
    success "Python DSL tests passed"
else
    error "Python DSL tests failed"
fi
echo ""

# Test 6: File Operations
echo "=== Test 6: File Operations ==="
info "Testing file operations"
echo '{"test":"data","value":123}' > /tmp/test.json
sq file /tmp/test.json --json --save /tmp/test_output.json
if [ -f /tmp/test_output.json ]; then
    success "File operations working"
else
    error "File operations failed"
fi
echo ""

# Test 7: Base64 Encoding
echo "=== Test 7: Base64 Encoding ==="
info "Testing Base64 encoding"
echo "Hello World" > /tmp/test.txt
sq file /tmp/test.txt --base64 --save /tmp/encoded.txt
if [ -f /tmp/encoded.txt ]; then
    ENCODED=$(cat /tmp/encoded.txt)
    success "Base64 encoded: $ENCODED"
else
    error "Base64 encoding failed"
fi
echo ""

# Test 8: Pipeline Chaining
echo "=== Test 8: Pipeline Chaining ==="
info "Testing multi-step pipeline"
streamware "http://mock-api:8080/products" \
    --pipe "transform://json" \
    --pipe "file://write?path=/tmp/products.json" \
    > /dev/null 2>&1

if [ -f /tmp/products.json ]; then
    success "Pipeline chaining working"
else
    error "Pipeline chaining failed"
fi
echo ""

# Summary
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo ""
success "All basic tests completed!"
echo ""
echo "Created files:"
ls -lh /tmp/*.json /tmp/*.csv /tmp/*.txt 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Try more examples:"
echo "  sq get mock-api:8080/users --json"
echo "  sq postgres 'SELECT * FROM users' --csv"
echo "  python examples/basic_usage.py"
echo ""
