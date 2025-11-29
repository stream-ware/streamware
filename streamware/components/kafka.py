"""
Kafka Component for Streamware
"""

from __future__ import annotations
import json
from typing import Any, Optional, Iterator, Dict
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.debug("kafka-python not installed. Kafka components will not be available.")


@register("kafka")
class KafkaComponent(Component):
    """
    Kafka component for producing and consuming messages
    
    URI formats:
        kafka://produce?topic=events&bootstrap_servers=localhost:9092
        kafka://consume?topic=events&group=processor&bootstrap_servers=localhost:9092
        kafka://operation?topic=mytopic&...
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        if not KAFKA_AVAILABLE:
            raise ComponentError("Kafka support not available. Install with: pip install streamware[kafka]")
            
        self.operation = uri.path or uri.operation or "produce"
        self.topic = uri.get_param('topic')
        self.bootstrap_servers = uri.get_param('bootstrap_servers', 'localhost:9092')
        
        if not self.topic and self.operation != "list_topics":
            raise ComponentError("Kafka topic not specified")
            
    def process(self, data: Any) -> Any:
        """Process data based on Kafka operation"""
        if self.operation == "produce":
            return self._produce(data)
        elif self.operation == "consume":
            return self._consume()
        elif self.operation == "list_topics":
            return self._list_topics()
        else:
            raise ComponentError(f"Unknown Kafka operation: {self.operation}")
            
    def _produce(self, data: Any) -> Dict[str, Any]:
        """Produce message to Kafka topic"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            
            # Get optional parameters
            key = self.uri.get_param('key')
            partition = self.uri.get_param('partition')
            
            # Extract key from data if specified
            if not key and isinstance(data, dict):
                key_field = self.uri.get_param('key_field')
                if key_field and key_field in data:
                    key = str(data[key_field])
                    
            # Send message
            future = producer.send(
                self.topic,
                value=data,
                key=key,
                partition=partition
            )
            
            # Wait for confirmation
            record_metadata = future.get(timeout=10)
            
            producer.flush()
            producer.close()
            
            return {
                "success": True,
                "topic": record_metadata.topic,
                "partition": record_metadata.partition,
                "offset": record_metadata.offset
            }
            
        except KafkaError as e:
            raise ConnectionError(f"Kafka produce error: {e}")
            
    def _consume(self) -> Any:
        """Consume message from Kafka topic"""
        try:
            group_id = self.uri.get_param('group', 'streamware-consumer')
            auto_offset_reset = self.uri.get_param('auto_offset_reset', 'latest')
            max_messages = self.uri.get_param('max_messages', 1)
            timeout_ms = self.uri.get_param('timeout_ms', 5000)
            
            consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=True,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                consumer_timeout_ms=timeout_ms
            )
            
            messages = []
            for i, message in enumerate(consumer):
                if i >= max_messages:
                    break
                    
                messages.append({
                    "value": message.value,
                    "key": message.key.decode('utf-8') if message.key else None,
                    "partition": message.partition,
                    "offset": message.offset,
                    "timestamp": message.timestamp
                })
                
            consumer.close()
            
            # Return single message if max_messages is 1
            if max_messages == 1 and messages:
                return messages[0]["value"]
            return messages
            
        except KafkaError as e:
            raise ConnectionError(f"Kafka consume error: {e}")
            
    def _list_topics(self) -> Dict[str, Any]:
        """List available Kafka topics"""
        try:
            consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers
            )
            topics = consumer.topics()
            consumer.close()
            
            return {
                "topics": list(topics),
                "count": len(topics)
            }
            
        except KafkaError as e:
            raise ConnectionError(f"Kafka connection error: {e}")


@register("kafka-produce")
class KafkaProduceComponent(Component):
    """Dedicated Kafka producer component"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "produce"
        self.kafka = KafkaComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.kafka._produce(data)


@register("kafka-consume")
class KafkaConsumeComponent(StreamComponent):
    """Dedicated Kafka consumer component with streaming support"""
    
    input_mime = None
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        if not KAFKA_AVAILABLE:
            raise ComponentError("Kafka support not available. Install with: pip install streamware[kafka]")
            
        self.topic = uri.get_param('topic')
        self.bootstrap_servers = uri.get_param('bootstrap_servers', 'localhost:9092')
        self.group_id = uri.get_param('group', 'streamware-consumer')
        self.auto_offset_reset = uri.get_param('auto_offset_reset', 'latest')
        
        if not self.topic:
            raise ComponentError("Kafka topic not specified")
            
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream messages from Kafka topic"""
        try:
            consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=True,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            logger.info(f"Starting Kafka consumer for topic: {self.topic}")
            
            try:
                for message in consumer:
                    yield {
                        "value": message.value,
                        "key": message.key.decode('utf-8') if message.key else None,
                        "partition": message.partition,
                        "offset": message.offset,
                        "timestamp": message.timestamp,
                        "topic": message.topic
                    }
                    
            finally:
                consumer.close()
                
        except KafkaError as e:
            raise ConnectionError(f"Kafka streaming error: {e}")
            
    def process(self, data: Any) -> Any:
        """Non-streaming consume (gets batch of messages)"""
        messages = []
        max_messages = self.uri.get_param('max_messages', 10)
        
        for i, message in enumerate(self.stream(None)):
            messages.append(message)
            if i >= max_messages - 1:
                break
                
        return messages


@register("kafka-batch")
class KafkaBatchComponent(Component):
    """Batch producer for Kafka"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        if not KAFKA_AVAILABLE:
            raise ComponentError("Kafka support not available. Install with: pip install streamware[kafka]")
            
        self.topic = uri.get_param('topic')
        self.bootstrap_servers = uri.get_param('bootstrap_servers', 'localhost:9092')
        
        if not self.topic:
            raise ComponentError("Kafka topic not specified")
            
    def process(self, data: Any) -> Dict[str, Any]:
        """Send batch of messages to Kafka"""
        if not isinstance(data, list):
            data = [data]
            
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                batch_size=16384,
                linger_ms=10
            )
            
            futures = []
            key_field = self.uri.get_param('key_field')
            
            for item in data:
                key = None
                if key_field and isinstance(item, dict) and key_field in item:
                    key = str(item[key_field])
                    
                future = producer.send(self.topic, value=item, key=key)
                futures.append(future)
                
            # Wait for all messages
            results = []
            for future in futures:
                record_metadata = future.get(timeout=10)
                results.append({
                    "partition": record_metadata.partition,
                    "offset": record_metadata.offset
                })
                
            producer.flush()
            producer.close()
            
            return {
                "success": True,
                "topic": self.topic,
                "messages_sent": len(results),
                "results": results
            }
            
        except KafkaError as e:
            raise ConnectionError(f"Kafka batch produce error: {e}")
