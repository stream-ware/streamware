"""
Streamware Examples - Demonstrating various pipeline patterns
"""

import asyncio
from streamware import flow, multicast, choose, split, join


def example_simple_pipeline():
    """Simple data transformation pipeline"""
    print("=== Simple Pipeline ===")
    
    result = (
        flow("http://api.example.com/users")
        | "transform://jsonpath?query=$[?(@.age>18)]"
        | "transform://csv"
        | "file://write?path=adults.csv"
    ).run()
    
    print(f"Result: {result}")


def example_curllm_web_scraping():
    """Web scraping with CurLLM and LLM"""
    print("=== CurLLM Web Scraping ===")
    
    result = (
        flow("curllm://browse?url=https://example.com&stealth=true")
        | "curllm://extract?instruction=Find all product prices under $50"
        | "transform://csv"
        | "file://write?path=products.csv"
    ).run()
    
    print(f"Extracted {len(result)} products")


def example_kafka_consumer():
    """Consume from Kafka and process messages"""
    print("=== Kafka Consumer ===")
    
    # Process Kafka messages continuously
    pipeline = (
        flow("kafka://consume?topic=events&group=processor")
        | "transform://jsonpath?query=$.data"
        | "validate://required=user_id,timestamp"
        | "postgres://insert?table=events"
    )
    
    # Run for 10 messages
    for i, result in enumerate(pipeline.stream()):
        print(f"Processed message {i+1}: {result}")
        if i >= 9:
            break


def example_multicast_pattern():
    """Send data to multiple destinations"""
    print("=== Multicast Pattern ===")
    
    data = {"event": "user_signup", "user_id": 123, "email": "user@example.com"}
    
    result = (
        flow("transform://enrich?source=api")
        | "multicast://destinations?list="
          "kafka://produce?topic=events,"
          "rabbitmq://publish?queue=notifications,"
          "file://append?path=events.log"
    ).run(data)
    
    print(f"Multicast results: {result}")


def example_conditional_routing():
    """Route data based on conditions"""
    print("=== Conditional Routing ===")
    
    # Using choose pattern
    pipeline = flow("http://api.example.com/orders")
    
    for order in [
        {"id": 1, "status": "pending", "amount": 100},
        {"id": 2, "status": "completed", "amount": 250},
        {"id": 3, "status": "cancelled", "amount": 50},
    ]:
        result = (
            pipeline
            | "choose://"
              "?when1=$.status=='pending'&then1=rabbitmq://publish?queue=pending"
              "&when2=$.status=='completed'&then2=postgres://insert?table=completed"
              "&otherwise=file://append?path=cancelled.log"
        ).run(order)
        
        print(f"Order {order['id']} routed: {result}")


def example_streaming_pipeline():
    """Process streaming data"""
    print("=== Streaming Pipeline ===")
    
    # Stream file lines through transformation
    pipeline = (
        flow("file-lines://path=data.jsonl")
        | "transform://json"
        | "filter://predicate=$.amount>100"
        | "aggregate://function=sum&window=10"
    )
    
    for batch in pipeline.stream():
        print(f"Batch sum: {batch}")


def example_split_join_pattern():
    """Split data for parallel processing then join"""
    print("=== Split/Join Pattern ===")
    
    data = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ]
    
    result = (
        flow("split://")
        | "curllm://extract?instruction=Enrich with random facts"
        | "join://strategy=list"
    ).run(data)
    
    print(f"Enriched data: {result}")


def example_file_watcher():
    """Watch directory for new files"""
    print("=== File Watcher ===")
    
    pipeline = (
        flow("file-watch://path=/tmp/uploads&pattern=*.csv")
        | "file://read"
        | "transform://csv"
        | "postgres://batch_insert?table=imports"
    )
    
    # Process first 5 new files
    for i, event in enumerate(pipeline.stream()):
        print(f"New file processed: {event}")
        if i >= 4:
            break


def example_rest_api_chain():
    """Chain multiple REST API calls"""
    print("=== REST API Chain ===")
    
    result = (
        flow("http://api1.example.com/user/123")
        | "transform://jsonpath?query=$.company_id"
        | "rest://api2.example.com/company/{company_id}"
        | "transform://jsonpath?query=$.address"
        | "graphql://api3.example.com?query=query($addr:String){geocode(address:$addr){lat,lng}}"
    ).run()
    
    print(f"Geocoded result: {result}")


def example_etl_pipeline():
    """Complete ETL pipeline"""
    print("=== ETL Pipeline ===")
    
    # Extract from PostgreSQL, transform, load to another database
    result = (
        flow("postgres://query?sql=SELECT * FROM raw_events WHERE date=CURRENT_DATE")
        | "transform://flatten"
        | "validate://required=user_id,event_type,timestamp"
        | "transform://template?template="
          "INSERT INTO processed_events (user_id, event, ts) "
          "VALUES ({{user_id}}, '{{event_type}}', '{{timestamp}}')"
        | "postgres://query?database=warehouse"
    ).run()
    
    print(f"ETL completed: {result} records processed")


async def example_async_pipeline():
    """Async pipeline execution"""
    print("=== Async Pipeline ===")
    
    # Run multiple pipelines concurrently
    pipelines = [
        flow(f"http://api.example.com/data/{i}") | "transform://json"
        for i in range(5)
    ]
    
    results = await asyncio.gather(
        *[p.run_async() for p in pipelines]
    )
    
    print(f"Async results: {len(results)} pipelines completed")


def example_curllm_form_automation():
    """Automate form filling with CurLLM"""
    print("=== CurLLM Form Automation ===")
    
    form_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "message": "I need a quote for my project"
    }
    
    result = (
        flow("curllm://browse?url=https://example.com/contact&visual=true")
        | f"curllm://fill_form?data={form_data}"
        | "curllm://screenshot"
    ).run()
    
    print(f"Form submitted: {result}")


def example_wordpress_automation():
    """Create WordPress posts via CurLLM"""
    print("=== WordPress Automation ===")
    
    posts = [
        {"title": "First Post", "content": "# Welcome\n\nThis is my first post"},
        {"title": "Second Post", "content": "# Update\n\nHere's an update"},
    ]
    
    for post in posts:
        result = (
            flow("curllm://api")
            .with_data({
                "wordpress_config": {
                    "url": "https://example.wordpress.com",
                    "username": "admin",
                    "password": "secret",
                    "action": "create_post",
                    "title": post["title"],
                    "content": post["content"],
                    "status": "draft"
                },
                "session_id": "wp-session"
            })
        ).run()
        
        print(f"Created post: {result}")


def example_rabbitmq_rpc():
    """RabbitMQ RPC pattern"""
    print("=== RabbitMQ RPC ===")
    
    # Send RPC request and wait for response
    request = {"method": "calculate", "params": {"a": 10, "b": 20}}
    
    result = (
        flow("rabbitmq-rpc://queue=calculator")
        .with_data(request)
    ).run()
    
    print(f"RPC result: {result}")


def example_metrics_monitoring():
    """Monitor pipeline metrics"""
    print("=== Metrics Monitoring ===")
    
    from streamware import metrics
    
    # Run pipeline with metrics tracking
    with metrics.track("data_processing"):
        result = (
            flow("http://api.example.com/data")
            | "transform://json"
            | "filter://predicate=$.active==true"
            | "postgres://insert?table=active_users"
        ).run()
    
    # Display metrics
    stats = metrics.get_stats("data_processing")
    print(f"Pipeline metrics: {stats}")
    
    # Print summary table
    metrics.print_summary()


if __name__ == "__main__":
    # Run examples
    examples = [
        example_simple_pipeline,
        example_multicast_pattern,
        example_conditional_routing,
        example_rest_api_chain,
        example_metrics_monitoring,
    ]
    
    for example in examples:
        try:
            example()
            print()
        except Exception as e:
            print(f"Example failed: {e}\n")
    
    # Run async example
    print("=== Running Async Example ===")
    asyncio.run(example_async_pipeline())
