"""
PostgreSQL Component for Streamware
"""

import json
from typing import Any, Optional, Iterator, Dict, List
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import sql
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.debug("psycopg2-binary not installed. PostgreSQL components will not be available.")

try:
    from sqlalchemy import create_engine, text, MetaData, Table
    from sqlalchemy.orm import sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger.debug("SQLAlchemy not installed. Some PostgreSQL features will be limited.")


@register("postgres")
@register("postgresql")
class PostgreSQLComponent(Component):
    """
    PostgreSQL component for database operations
    
    URI formats:
        postgres://query?sql=SELECT * FROM users&host=localhost&database=mydb
        postgres://insert?table=users&host=localhost&database=mydb
        postgres://update?table=users&where=id=1&host=localhost&database=mydb
        postgres://stream?table=users&events=insert,update
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        if not POSTGRES_AVAILABLE:
            raise ComponentError("PostgreSQL support not available. Install with: pip install streamware[postgres]")
            
        self.operation = uri.path or uri.operation or "query"
        self.host = uri.get_param('host', 'localhost')
        self.port = uri.get_param('port', 5432)
        self.database = uri.get_param('database', uri.get_param('db', 'postgres'))
        self.user = uri.get_param('user', uri.get_param('username', 'postgres'))
        self.password = uri.get_param('password', uri.get_param('pass', ''))
        
    def process(self, data: Any) -> Any:
        """Process data based on PostgreSQL operation"""
        if self.operation == "query":
            return self._query(data)
        elif self.operation == "insert":
            return self._insert(data)
        elif self.operation == "update":
            return self._update(data)
        elif self.operation == "delete":
            return self._delete(data)
        elif self.operation == "upsert":
            return self._upsert(data)
        elif self.operation == "stream":
            return self._stream()
        else:
            raise ComponentError(f"Unknown PostgreSQL operation: {self.operation}")
            
    def _get_connection(self):
        """Get PostgreSQL connection"""
        try:
            return psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=RealDictCursor
            )
        except psycopg2.Error as e:
            raise ConnectionError(f"PostgreSQL connection error: {e}")
            
    def _query(self, data: Any) -> Any:
        """Execute SELECT query"""
        sql_query = self.uri.get_param('sql') or self.uri.get_param('query')
        
        if not sql_query and isinstance(data, dict):
            sql_query = data.get('sql') or data.get('query')
        elif not sql_query and isinstance(data, str):
            sql_query = data
            
        if not sql_query:
            # Build query from parameters
            table = self.uri.get_param('table')
            if not table:
                raise ComponentError("No SQL query or table specified")
                
            where = self.uri.get_param('where')
            order_by = self.uri.get_param('order_by')
            limit = self.uri.get_param('limit')
            
            sql_query = f"SELECT * FROM {table}"
            if where:
                sql_query += f" WHERE {where}"
            if order_by:
                sql_query += f" ORDER BY {order_by}"
            if limit:
                sql_query += f" LIMIT {limit}"
                
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Handle parameterized queries
            params = None
            if isinstance(data, dict) and 'params' in data:
                params = data['params']
                
            cursor.execute(sql_query, params)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Convert to regular dicts
            return [dict(row) for row in results]
            
        except psycopg2.Error as e:
            raise ComponentError(f"PostgreSQL query error: {e}")
            
    def _insert(self, data: Any) -> Dict[str, Any]:
        """Insert data into table"""
        table = self.uri.get_param('table')
        if not table:
            raise ComponentError("Table not specified for insert")
            
        # Handle batch insert
        if isinstance(data, list):
            return self._batch_insert(table, data)
            
        if not isinstance(data, dict):
            raise ComponentError("Insert data must be a dictionary or list of dictionaries")
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build INSERT query
            columns = list(data.keys())
            values = list(data.values())
            placeholders = ', '.join(['%s'] * len(columns))
            columns_str = ', '.join(columns)
            
            query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) RETURNING *"
            
            cursor.execute(query, values)
            result = cursor.fetchone()
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "operation": "insert",
                "table": table,
                "data": dict(result) if result else None
            }
            
        except psycopg2.Error as e:
            raise ComponentError(f"PostgreSQL insert error: {e}")
            
    def _batch_insert(self, table: str, data: List[Dict]) -> Dict[str, Any]:
        """Insert multiple records"""
        if not data:
            return {"success": True, "rows_inserted": 0}
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get columns from first record
            columns = list(data[0].keys())
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))
            
            query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            
            # Prepare values
            values_list = []
            for record in data:
                values = [record.get(col) for col in columns]
                values_list.append(values)
                
            # Execute batch insert
            cursor.executemany(query, values_list)
            rows_inserted = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "operation": "batch_insert",
                "table": table,
                "rows_inserted": rows_inserted
            }
            
        except psycopg2.Error as e:
            raise ComponentError(f"PostgreSQL batch insert error: {e}")
            
    def _update(self, data: Any) -> Dict[str, Any]:
        """Update records in table"""
        table = self.uri.get_param('table')
        where = self.uri.get_param('where')
        
        if not table:
            raise ComponentError("Table not specified for update")
            
        if not isinstance(data, dict):
            raise ComponentError("Update data must be a dictionary")
            
        # Extract where clause from data if not in URI
        if not where and 'where' in data:
            where = data['where']
            data = {k: v for k, v in data.items() if k != 'where'}
            
        if not where:
            raise ComponentError("WHERE clause required for update")
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build UPDATE query
            set_parts = []
            values = []
            for key, value in data.items():
                set_parts.append(f"{key} = %s")
                values.append(value)
                
            set_clause = ', '.join(set_parts)
            query = f"UPDATE {table} SET {set_clause} WHERE {where} RETURNING *"
            
            cursor.execute(query, values)
            results = cursor.fetchall()
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "operation": "update",
                "table": table,
                "rows_updated": len(results),
                "data": [dict(row) for row in results]
            }
            
        except psycopg2.Error as e:
            raise ComponentError(f"PostgreSQL update error: {e}")
            
    def _delete(self, data: Any) -> Dict[str, Any]:
        """Delete records from table"""
        table = self.uri.get_param('table')
        where = self.uri.get_param('where')
        
        if not table:
            raise ComponentError("Table not specified for delete")
            
        # Get where clause from data if not in URI
        if not where and isinstance(data, dict):
            where = data.get('where')
            
        if not where:
            raise ComponentError("WHERE clause required for delete")
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = f"DELETE FROM {table} WHERE {where} RETURNING *"
            
            cursor.execute(query)
            deleted = cursor.fetchall()
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "operation": "delete",
                "table": table,
                "rows_deleted": len(deleted),
                "data": [dict(row) for row in deleted]
            }
            
        except psycopg2.Error as e:
            raise ComponentError(f"PostgreSQL delete error: {e}")
            
    def _upsert(self, data: Any) -> Dict[str, Any]:
        """Insert or update (UPSERT) using ON CONFLICT"""
        table = self.uri.get_param('table')
        conflict_key = self.uri.get_param('key') or self.uri.get_param('conflict')
        
        if not table:
            raise ComponentError("Table not specified for upsert")
        if not conflict_key:
            raise ComponentError("Conflict key not specified for upsert")
            
        if isinstance(data, list):
            return self._batch_upsert(table, conflict_key, data)
            
        if not isinstance(data, dict):
            raise ComponentError("Upsert data must be a dictionary or list")
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            columns = list(data.keys())
            values = list(data.values())
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))
            
            # Build UPDATE clause for conflict
            update_parts = []
            for col in columns:
                if col != conflict_key:
                    update_parts.append(f"{col} = EXCLUDED.{col}")
            update_clause = ', '.join(update_parts)
            
            query = f"""
                INSERT INTO {table} ({columns_str}) VALUES ({placeholders})
                ON CONFLICT ({conflict_key}) DO UPDATE SET {update_clause}
                RETURNING *
            """
            
            cursor.execute(query, values)
            result = cursor.fetchone()
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "operation": "upsert",
                "table": table,
                "data": dict(result) if result else None
            }
            
        except psycopg2.Error as e:
            raise ComponentError(f"PostgreSQL upsert error: {e}")
            
    def _batch_upsert(self, table: str, conflict_key: str, data: List[Dict]) -> Dict[str, Any]:
        """Batch upsert operation"""
        if not data:
            return {"success": True, "rows_upserted": 0}
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Process each record
            rows_affected = 0
            for record in data:
                columns = list(record.keys())
                values = list(record.values())
                columns_str = ', '.join(columns)
                placeholders = ', '.join(['%s'] * len(columns))
                
                update_parts = []
                for col in columns:
                    if col != conflict_key:
                        update_parts.append(f"{col} = EXCLUDED.{col}")
                update_clause = ', '.join(update_parts)
                
                query = f"""
                    INSERT INTO {table} ({columns_str}) VALUES ({placeholders})
                    ON CONFLICT ({conflict_key}) DO UPDATE SET {update_clause}
                """
                
                cursor.execute(query, values)
                rows_affected += cursor.rowcount
                
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "operation": "batch_upsert",
                "table": table,
                "rows_upserted": rows_affected
            }
            
        except psycopg2.Error as e:
            raise ComponentError(f"PostgreSQL batch upsert error: {e}")
            
    def _stream(self) -> Any:
        """Stream changes from table (simplified CDC)"""
        # This is a simplified implementation
        # For production, consider using logical replication or triggers
        raise NotImplementedError("PostgreSQL streaming not yet implemented. Consider using Debezium or logical replication.")


@register("postgres-query")
class PostgresQueryComponent(Component):
    """Dedicated PostgreSQL query component"""
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "query"
        self.postgres = PostgreSQLComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.postgres._query(data)


@register("postgres-insert")
class PostgresInsertComponent(Component):
    """Dedicated PostgreSQL insert component"""
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "insert"
        self.postgres = PostgreSQLComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.postgres._insert(data)


@register("postgres-stream")
class PostgresStreamComponent(StreamComponent):
    """PostgreSQL streaming component (placeholder for CDC functionality)"""
    
    input_mime = None
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        logger.warning("PostgreSQL streaming is not fully implemented. Consider using Debezium for production CDC.")
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream changes from PostgreSQL"""
        # Placeholder implementation
        # In production, this would connect to logical replication slot
        # or use triggers with LISTEN/NOTIFY
        yield {"message": "PostgreSQL streaming not implemented"}
        
    def process(self, data: Any) -> Any:
        return {"message": "PostgreSQL streaming not implemented"}
