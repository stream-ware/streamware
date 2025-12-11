"""
RabbitMQ Component for Streamware
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
    import pika
    from pika.exceptions import AMQPError
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False
    logger.debug("pika not installed. RabbitMQ components will not be available.")


@register("rabbitmq")
class RabbitMQComponent(Component):
    """
    RabbitMQ component for publishing and consuming messages
    
    URI formats:
        rabbitmq://publish?exchange=myexchange&routing_key=mykey
        rabbitmq://consume?queue=myqueue&auto_ack=true
        rabbitmq://operation?param=value
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        if not RABBITMQ_AVAILABLE:
            raise ComponentError("RabbitMQ support not available. Install with: pip install streamware[rabbitmq]")
            
        self.operation = uri.path or uri.operation or "publish"
        self.host = uri.get_param('host', 'localhost')
        self.port = uri.get_param('port', 5672)
        self.username = uri.get_param('username', 'guest')
        self.password = uri.get_param('password', 'guest')
        self.virtual_host = uri.get_param('vhost', '/')
        
    def process(self, data: Any) -> Any:
        """Process data based on RabbitMQ operation"""
        if self.operation == "publish":
            return self._publish(data)
        elif self.operation == "consume":
            return self._consume()
        elif self.operation == "declare_exchange":
            return self._declare_exchange()
        elif self.operation == "declare_queue":
            return self._declare_queue()
        else:
            raise ComponentError(f"Unknown RabbitMQ operation: {self.operation}")
            
    def _get_connection(self) -> pika.BlockingConnection:
        """Get RabbitMQ connection"""
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.virtual_host,
            credentials=credentials
        )
        return pika.BlockingConnection(parameters)
        
    def _publish(self, data: Any) -> Dict[str, Any]:
        """Publish message to RabbitMQ"""
        try:
            exchange = self.uri.get_param('exchange', '')
            routing_key = self.uri.get_param('routing_key', '')
            queue = self.uri.get_param('queue')
            
            # If queue is specified but not routing key, use queue as routing key
            if queue and not routing_key:
                routing_key = queue
                
            connection = self._get_connection()
            channel = connection.channel()
            
            # Declare exchange if specified
            if exchange and exchange != '':
                exchange_type = self.uri.get_param('exchange_type', 'direct')
                durable = self.uri.get_param('durable', True)
                channel.exchange_declare(
                    exchange=exchange,
                    exchange_type=exchange_type,
                    durable=durable
                )
                
            # Declare queue if specified
            if queue:
                channel.queue_declare(queue=queue, durable=True)
                
            # Prepare message
            if isinstance(data, str):
                message = data
            else:
                message = json.dumps(data)
                
            # Publish message
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            connection.close()
            
            return {
                "success": True,
                "exchange": exchange,
                "routing_key": routing_key,
                "message_size": len(message)
            }
            
        except AMQPError as e:
            raise ConnectionError(f"RabbitMQ publish error: {e}")
            
    def _consume(self) -> Any:
        """Consume message from RabbitMQ"""
        try:
            queue = self.uri.get_param('queue')
            if not queue:
                raise ComponentError("Queue not specified for consume operation")
                
            auto_ack = self.uri.get_param('auto_ack', True)
            max_messages = self.uri.get_param('max_messages', 1)
            timeout = self.uri.get_param('timeout', 5)
            
            connection = self._get_connection()
            channel = connection.channel()
            
            # Declare queue to ensure it exists
            channel.queue_declare(queue=queue, durable=True)
            
            messages = []
            
            for method_frame, properties, body in channel.consume(
                queue=queue,
                auto_ack=auto_ack,
                inactivity_timeout=timeout
            ):
                if method_frame is None:
                    break
                    
                # Parse message body
                try:
                    message_data = json.loads(body)
                except json.JSONDecodeError:
                    message_data = body.decode('utf-8')
                    
                messages.append({
                    "data": message_data,
                    "routing_key": method_frame.routing_key,
                    "exchange": method_frame.exchange,
                    "delivery_tag": method_frame.delivery_tag,
                    "redelivered": method_frame.redelivered
                })
                
                if not auto_ack:
                    channel.basic_ack(method_frame.delivery_tag)
                    
                if len(messages) >= max_messages:
                    break
                    
            channel.cancel()
            connection.close()
            
            # Return single message if max_messages is 1
            if max_messages == 1 and messages:
                return messages[0]["data"]
            return messages
            
        except AMQPError as e:
            raise ConnectionError(f"RabbitMQ consume error: {e}")
            
    def _declare_exchange(self) -> Dict[str, Any]:
        """Declare an exchange"""
        try:
            exchange = self.uri.get_param('exchange')
            if not exchange:
                raise ComponentError("Exchange name not specified")
                
            exchange_type = self.uri.get_param('type', 'direct')
            durable = self.uri.get_param('durable', True)
            
            connection = self._get_connection()
            channel = connection.channel()
            
            channel.exchange_declare(
                exchange=exchange,
                exchange_type=exchange_type,
                durable=durable
            )
            
            connection.close()
            
            return {
                "success": True,
                "exchange": exchange,
                "type": exchange_type,
                "durable": durable
            }
            
        except AMQPError as e:
            raise ConnectionError(f"RabbitMQ exchange declare error: {e}")
            
    def _declare_queue(self) -> Dict[str, Any]:
        """Declare a queue"""
        try:
            queue = self.uri.get_param('queue')
            if not queue:
                raise ComponentError("Queue name not specified")
                
            durable = self.uri.get_param('durable', True)
            exclusive = self.uri.get_param('exclusive', False)
            auto_delete = self.uri.get_param('auto_delete', False)
            
            connection = self._get_connection()
            channel = connection.channel()
            
            result = channel.queue_declare(
                queue=queue,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete
            )
            
            connection.close()
            
            return {
                "success": True,
                "queue": result.method.queue,
                "message_count": result.method.message_count,
                "consumer_count": result.method.consumer_count
            }
            
        except AMQPError as e:
            raise ConnectionError(f"RabbitMQ queue declare error: {e}")


@register("rabbitmq-publish")
class RabbitMQPublishComponent(Component):
    """Dedicated RabbitMQ publisher component"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "publish"
        self.rabbitmq = RabbitMQComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.rabbitmq._publish(data)


@register("rabbitmq-consume")
class RabbitMQConsumeComponent(StreamComponent):
    """Dedicated RabbitMQ consumer component with streaming support"""
    
    input_mime = None
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        if not RABBITMQ_AVAILABLE:
            raise ComponentError("RabbitMQ support not available. Install with: pip install streamware[rabbitmq]")
            
        self.queue = uri.get_param('queue')
        if not self.queue:
            raise ComponentError("Queue not specified")
            
        self.rabbitmq = RabbitMQComponent(uri)
        self.auto_ack = uri.get_param('auto_ack', True)
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream messages from RabbitMQ queue"""
        try:
            connection = self.rabbitmq._get_connection()
            channel = connection.channel()
            
            # Declare queue to ensure it exists
            channel.queue_declare(queue=self.queue, durable=True)
            
            # Set QoS
            channel.basic_qos(prefetch_count=1)
            
            logger.info(f"Starting RabbitMQ consumer for queue: {self.queue}")
            
            def callback(ch, method, properties, body):
                """Callback for message consumption"""
                try:
                    message_data = json.loads(body)
                except json.JSONDecodeError:
                    message_data = body.decode('utf-8')
                    
                return {
                    "data": message_data,
                    "routing_key": method.routing_key,
                    "exchange": method.exchange,
                    "delivery_tag": method.delivery_tag,
                    "redelivered": method.redelivered,
                    "properties": {
                        "content_type": properties.content_type,
                        "delivery_mode": properties.delivery_mode
                    }
                }
                
            # Start consuming
            for method_frame, properties, body in channel.consume(
                queue=self.queue,
                auto_ack=self.auto_ack
            ):
                if method_frame is None:
                    continue
                    
                message = callback(channel, method_frame, properties, body)
                yield message
                
                if not self.auto_ack:
                    channel.basic_ack(method_frame.delivery_tag)
                    
        except AMQPError as e:
            raise ConnectionError(f"RabbitMQ streaming error: {e}")
        finally:
            try:
                connection.close()
            except Exception:
                pass
                
    def process(self, data: Any) -> Any:
        """Non-streaming consume (gets batch of messages)"""
        return self.rabbitmq._consume()


@register("rabbitmq-rpc")
class RabbitMQRPCComponent(Component):
    """RabbitMQ RPC pattern implementation"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        if not RABBITMQ_AVAILABLE:
            raise ComponentError("RabbitMQ support not available. Install with: pip install streamware[rabbitmq]")
            
        self.rpc_queue = uri.get_param('queue', 'rpc_queue')
        self.timeout = uri.get_param('timeout', 10)
        self.rabbitmq = RabbitMQComponent(uri)
        
    def process(self, data: Any) -> Any:
        """Make RPC call via RabbitMQ"""
        import uuid
        
        try:
            connection = self.rabbitmq._get_connection()
            channel = connection.channel()
            
            # Create exclusive callback queue
            result = channel.queue_declare(queue='', exclusive=True)
            callback_queue = result.method.queue
            
            correlation_id = str(uuid.uuid4())
            response = None
            
            def on_response(ch, method, props, body):
                nonlocal response
                if correlation_id == props.correlation_id:
                    response = json.loads(body)
                    
            channel.basic_consume(
                queue=callback_queue,
                on_message_callback=on_response,
                auto_ack=True
            )
            
            # Send RPC request
            channel.basic_publish(
                exchange='',
                routing_key=self.rpc_queue,
                properties=pika.BasicProperties(
                    reply_to=callback_queue,
                    correlation_id=correlation_id,
                    content_type='application/json'
                ),
                body=json.dumps(data)
            )
            
            # Wait for response
            start_time = pika.time.time()
            while response is None:
                connection.process_data_events(time_limit=0.1)
                if pika.time.time() - start_time > self.timeout:
                    raise TimeoutError(f"RPC timeout after {self.timeout} seconds")
                    
            connection.close()
            return response
            
        except AMQPError as e:
            raise ConnectionError(f"RabbitMQ RPC error: {e}")
