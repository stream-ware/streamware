#!/bin/bash
# Kafka to PostgreSQL Pipeline Service
# Continuously consumes Kafka messages and stores in PostgreSQL

SERVICE_NAME="streamware-kafka-postgres"
LOG_FILE="/logs/${SERVICE_NAME}.log"
PID_FILE="/tmp/${SERVICE_NAME}.pid"

KAFKA_TOPIC="${KAFKA_TOPIC:-events}"
KAFKA_GROUP="${KAFKA_GROUP:-db-writer}"
POSTGRES_TABLE="${POSTGRES_TABLE:-events}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

process_stream() {
    log "Starting Kafka → PostgreSQL pipeline"
    log "Topic: $KAFKA_TOPIC, Table: $POSTGRES_TABLE"
    
    # Stream Kafka to PostgreSQL
    streamware "kafka://consume?topic=${KAFKA_TOPIC}&group=${KAFKA_GROUP}" \
        --pipe "transform://json" \
        --pipe "postgres://insert?table=${POSTGRES_TABLE}" \
        --stream 2>&1 | tee -a "$LOG_FILE"
}

main() {
    mkdir -p /logs
    echo $$ > "$PID_FILE"
    
    log "Service started"
    process_stream
}

cleanup() {
    log "Service stopped"
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

main
