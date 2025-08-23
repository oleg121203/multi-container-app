"""
Redis MCP Server - Enhanced Redis management and operations
Provides advanced Redis operations, cluster management, and data analysis
"""
import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

logger = logging.getLogger(__name__)

class RedisOperation(BaseModel):
    operation: str
    key: Optional[str] = None
    value: Optional[Any] = None
    params: Dict[str, Any] = {}

class RedisResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float

class RedisStats(BaseModel):
    total_keys: int
    memory_usage: str
    connected_clients: int
    keyspace_hits: int
    keyspace_misses: int
    uptime_seconds: int

class RedisMCPServer:
    """Enhanced Redis MCP Server with cluster support and analytics"""
    
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.port = int(os.getenv('MCP_SERVER_PORT', '4005'))
        self.redis_client = None
        self.app = FastAPI(title="Redis MCP Server", version="1.0.0")
        self._setup_routes()
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            # Try cluster connection first
            if 'cluster' in self.redis_url.lower():
                self.redis_client = RedisCluster.from_url(self.redis_url)
            else:
                self.redis_client = redis.from_url(self.redis_url)
            
            # Test connection
            await self.redis_client.ping()
            logger.info(f"Connected to Redis: {self.redis_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            try:
                if self.redis_client:
                    await self.redis_client.ping()
                    return {"status": "healthy", "redis_connected": True}
                return {"status": "unhealthy", "redis_connected": False}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}
        
        @self.app.post("/execute", response_model=RedisResponse)
        async def execute_operation(operation: RedisOperation):
            """Execute Redis operation"""
            return await self.execute_redis_operation(operation)
        
        @self.app.get("/stats", response_model=RedisStats)
        async def get_redis_stats():
            """Get Redis server statistics"""
            return await self.get_server_stats()
        
        @self.app.get("/keys")
        async def list_keys(pattern: str = "*", limit: int = 100):
            """List Redis keys with pattern"""
            return await self.list_keys_with_pattern(pattern, limit)
        
        @self.app.post("/bulk_operations")
        async def bulk_operations(operations: List[RedisOperation]):
            """Execute multiple Redis operations"""
            return await self.execute_bulk_operations(operations)
        
        @self.app.get("/memory_analysis")
        async def memory_analysis():
            """Analyze Redis memory usage"""
            return await self.analyze_memory_usage()
        
        @self.app.post("/backup")
        async def create_backup(keys_pattern: str = "*"):
            """Create backup of Redis data"""
            return await self.create_data_backup(keys_pattern)
        
        @self.app.post("/restore")
        async def restore_backup(backup_data: dict):
            """Restore Redis data from backup"""
            return await self.restore_data_backup(backup_data)
    
    async def execute_redis_operation(self, operation: RedisOperation) -> RedisResponse:
        """Execute a Redis operation with timing"""
        start_time = datetime.now()
        
        try:
            if not self.redis_client:
                raise Exception("Redis client not initialized")
            
            result = await self._perform_operation(operation)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return RedisResponse(
                success=True,
                result=result,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Redis operation failed: {e}")
            
            return RedisResponse(
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    async def _perform_operation(self, operation: RedisOperation) -> Any:
        """Perform the actual Redis operation"""
        if not self.redis_client:
            raise Exception("Redis client not initialized")
            
        op = operation.operation.lower()
        key = operation.key
        value = operation.value
        params = operation.params
        
        # Validate required parameters
        if key is None and op not in ['flushdb', 'scan']:
            raise ValueError("Key is required for this operation")
        
        # Basic operations
        if op == "get":
            if key is None:
                raise ValueError("Key is required for get operation")
            result = await self.redis_client.get(key)
            return result.decode('utf-8') if result else None
        
        elif op == "set":
            if key is None or value is None:
                raise ValueError("Key and value are required for set operation")
            ex = params.get('ex')  # expiration in seconds
            nx = params.get('nx', False)  # only if not exists
            xx = params.get('xx', False)  # only if exists
            return await self.redis_client.set(key, value, ex=ex, nx=nx, xx=xx)
        
        elif op == "delete" or op == "del":
            return await self.redis_client.delete(key)
        
        elif op == "exists":
            return await self.redis_client.exists(key)
        
        elif op == "expire":
            seconds = params.get('seconds', 3600)
            return await self.redis_client.expire(key, seconds)
        
        elif op == "ttl":
            return await self.redis_client.ttl(key)
        
        # List operations
        elif op == "lpush":
            return await self.redis_client.lpush(key, value)
        
        elif op == "rpush":
            return await self.redis_client.rpush(key, value)
        
        elif op == "lpop":
            result = await self.redis_client.lpop(key)
            return result.decode('utf-8') if result else None
        
        elif op == "rpop":
            result = await self.redis_client.rpop(key)
            return result.decode('utf-8') if result else None
        
        elif op == "lrange":
            start = params.get('start', 0)
            end = params.get('end', -1)
            results = await self.redis_client.lrange(key, start, end)
            return [r.decode('utf-8') for r in results]
        
        elif op == "llen":
            return await self.redis_client.llen(key)
        
        # Hash operations
        elif op == "hset":
            field = params.get('field')
            return await self.redis_client.hset(key, field, value)
        
        elif op == "hget":
            field = params.get('field')
            result = await self.redis_client.hget(key, field)
            return result.decode('utf-8') if result else None
        
        elif op == "hgetall":
            results = await self.redis_client.hgetall(key)
            return {k.decode('utf-8'): v.decode('utf-8') for k, v in results.items()}
        
        elif op == "hdel":
            field = params.get('field')
            return await self.redis_client.hdel(key, field)
        
        # Set operations
        elif op == "sadd":
            return await self.redis_client.sadd(key, value)
        
        elif op == "srem":
            return await self.redis_client.srem(key, value)
        
        elif op == "smembers":
            results = await self.redis_client.smembers(key)
            return [r.decode('utf-8') for r in results]
        
        elif op == "sismember":
            return await self.redis_client.sismember(key, value)
        
        # Sorted set operations
        elif op == "zadd":
            score = params.get('score', 0)
            return await self.redis_client.zadd(key, {value: score})
        
        elif op == "zrange":
            start = params.get('start', 0)
            end = params.get('end', -1)
            withscores = params.get('withscores', False)
            results = await self.redis_client.zrange(key, start, end, withscores=withscores)
            if withscores:
                return [(r[0].decode('utf-8'), r[1]) for r in results]
            return [r.decode('utf-8') for r in results]
        
        elif op == "zrem":
            return await self.redis_client.zrem(key, value)
        
        # Advanced operations
        elif op == "flushdb":
            return await self.redis_client.flushdb()
        
        elif op == "scan":
            cursor = params.get('cursor', 0)
            match = params.get('match', '*')
            count = params.get('count', 10)
            return await self.redis_client.scan(cursor=cursor, match=match, count=count)
        
        else:
            raise ValueError(f"Unsupported operation: {op}")
    
    async def get_server_stats(self) -> RedisStats:
        """Get Redis server statistics"""
        try:
            info = await self.redis_client.info()
            
            return RedisStats(
                total_keys=info.get('db0', {}).get('keys', 0),
                memory_usage=info.get('used_memory_human', '0B'),
                connected_clients=info.get('connected_clients', 0),
                keyspace_hits=info.get('keyspace_hits', 0),
                keyspace_misses=info.get('keyspace_misses', 0),
                uptime_seconds=info.get('uptime_in_seconds', 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_keys_with_pattern(self, pattern: str, limit: int) -> List[str]:
        """List keys matching pattern"""
        try:
            keys = []
            cursor = 0
            
            while len(keys) < limit:
                cursor, batch_keys = await self.redis_client.scan(
                    cursor=cursor, 
                    match=pattern, 
                    count=min(100, limit - len(keys))
                )
                
                keys.extend([key.decode('utf-8') for key in batch_keys])
                
                if cursor == 0:  # Full scan completed
                    break
            
            return keys[:limit]
            
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_bulk_operations(self, operations: List[RedisOperation]) -> List[RedisResponse]:
        """Execute multiple operations in sequence"""
        results = []
        
        for operation in operations:
            result = await self.execute_redis_operation(operation)
            results.append(result)
        
        return results
    
    async def analyze_memory_usage(self) -> Dict[str, Any]:
        """Analyze Redis memory usage patterns"""
        try:
            info = await self.redis_client.info('memory')
            
            # Get sample of keys for analysis
            sample_keys = await self.list_keys_with_pattern("*", 100)
            key_analysis = {}
            
            for key in sample_keys[:20]:  # Analyze first 20 keys
                try:
                    memory_usage = await self.redis_client.memory_usage(key)
                    key_type = await self.redis_client.type(key)
                    ttl = await self.redis_client.ttl(key)
                    
                    key_analysis[key] = {
                        'memory_bytes': memory_usage,
                        'type': key_type.decode('utf-8') if key_type else 'unknown',
                        'ttl': ttl
                    }
                except Exception:
                    # Skip keys that can't be analyzed
                    continue
            
            return {
                'total_memory': info.get('used_memory', 0),
                'peak_memory': info.get('used_memory_peak', 0),
                'fragmentation_ratio': info.get('mem_fragmentation_ratio', 0),
                'key_analysis': key_analysis,
                'memory_efficiency': {
                    'total_keys_analyzed': len(key_analysis),
                    'avg_key_size': sum(k['memory_bytes'] for k in key_analysis.values()) / len(key_analysis) if key_analysis else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Memory analysis failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_data_backup(self, keys_pattern: str) -> Dict[str, Any]:
        """Create backup of Redis data"""
        try:
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'pattern': keys_pattern,
                'data': {}
            }
            
            keys = await self.list_keys_with_pattern(keys_pattern, 1000)
            
            for key in keys:
                try:
                    key_type = await self.redis_client.type(key)
                    key_type_str = key_type.decode('utf-8') if key_type else 'string'
                    ttl = await self.redis_client.ttl(key)
                    
                    if key_type_str == 'string':
                        value = await self.redis_client.get(key)
                        backup_data['data'][key] = {
                            'type': 'string',
                            'value': value.decode('utf-8') if value else None,
                            'ttl': ttl
                        }
                    elif key_type_str == 'list':
                        value = await self.redis_client.lrange(key, 0, -1)
                        backup_data['data'][key] = {
                            'type': 'list',
                            'value': [v.decode('utf-8') for v in value],
                            'ttl': ttl
                        }
                    elif key_type_str == 'hash':
                        value = await self.redis_client.hgetall(key)
                        backup_data['data'][key] = {
                            'type': 'hash',
                            'value': {k.decode('utf-8'): v.decode('utf-8') for k, v in value.items()},
                            'ttl': ttl
                        }
                    elif key_type_str == 'set':
                        value = await self.redis_client.smembers(key)
                        backup_data['data'][key] = {
                            'type': 'set',
                            'value': [v.decode('utf-8') for v in value],
                            'ttl': ttl
                        }
                        
                except Exception as e:
                    logger.warning(f"Failed to backup key {key}: {e}")
                    continue
            
            return {
                'backup_created': True,
                'keys_backed_up': len(backup_data['data']),
                'backup_size_keys': len(backup_data['data']),
                'backup_data': backup_data
            }
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def restore_data_backup(self, backup_data: dict) -> Dict[str, Any]:
        """Restore Redis data from backup"""
        try:
            restored_keys = 0
            failed_keys = []
            
            data = backup_data.get('data', {})
            
            for key, key_data in data.items():
                try:
                    key_type = key_data.get('type', 'string')
                    value = key_data.get('value')
                    ttl = key_data.get('ttl', -1)
                    
                    if key_type == 'string':
                        await self.redis_client.set(key, value)
                    elif key_type == 'list':
                        await self.redis_client.delete(key)  # Clear existing
                        if value:
                            await self.redis_client.rpush(key, *value)
                    elif key_type == 'hash':
                        await self.redis_client.delete(key)  # Clear existing
                        if value:
                            await self.redis_client.hset(key, mapping=value)
                    elif key_type == 'set':
                        await self.redis_client.delete(key)  # Clear existing
                        if value:
                            await self.redis_client.sadd(key, *value)
                    
                    # Set TTL if specified
                    if ttl > 0:
                        await self.redis_client.expire(key, ttl)
                    
                    restored_keys += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to restore key {key}: {e}")
                    failed_keys.append(key)
                    continue
            
            return {
                'restore_completed': True,
                'keys_restored': restored_keys,
                'failed_keys': failed_keys,
                'total_keys_in_backup': len(data)
            }
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def shutdown(self):
        """Shutdown the Redis client"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def run_server(self):
        """Run the FastAPI server"""
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

async def main():
    server = RedisMCPServer()
    try:
        await server.initialize()
        await server.run_server()
    finally:
        await server.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
