"""
Linear API tool for issue management
GraphQL client with retry/circuit-breaker pattern
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time

import httpx
from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport

from .config import config

logger = logging.getLogger(__name__)


class IssueState(str, Enum):
    BACKLOG = "backlog"
    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"


class IssuePriority(int, Enum):
    NO_PRIORITY = 0
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class LinearIssue:
    id: str
    title: str
    description: Optional[str]
    state: IssueState
    priority: IssuePriority
    url: str
    identifier: str
    team_id: str
    created_at: str
    updated_at: str


@dataclass
class LinearTeam:
    id: str
    name: str
    key: str


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def call(self, func):
        """Decorator to wrap functions with circuit breaker"""
        async def wrapper(*args, **kwargs):
            if self.state == CircuitBreakerState.OPEN:
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _on_success(self):
        """Reset circuit breaker on success"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN


class LinearClient:
    """Linear API client with retry and circuit breaker"""
    
    def __init__(self, api_key: str = None, max_retries: int = 3):
        self.api_key = api_key or config.LINEAR_API_KEY
        self.max_retries = max_retries
        self.client = None
        self.circuit_breaker = CircuitBreaker()
        
        if not self.api_key:
            raise ValueError("Linear API key is required")
    
    async def initialize(self):
        """Initialize the GraphQL client"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        transport = HTTPXAsyncTransport(url=config.LINEAR_API_URL, headers=headers)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)
        logger.info("Linear client initialized")
    
    async def close(self):
        """Close the client"""
        if self.client:
            await self.client.transport.close()
    
    async def _execute_with_retry(self, query, variables: Dict = None):
        """Execute GraphQL query with retry logic"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                @self.circuit_breaker.call
                async def _execute():
                    return await self.client.execute_async(query, variable_values=variables)
                
                return await _execute()
            
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed")
        
        raise last_exception
    
    async def get_teams(self) -> List[LinearTeam]:
        """Get all teams"""
        query = gql("""
            query GetTeams {
                teams {
                    nodes {
                        id
                        name
                        key
                    }
                }
            }
        """)
        
        result = await self._execute_with_retry(query)
        teams = []
        for team_data in result["teams"]["nodes"]:
            team = LinearTeam(
                id=team_data["id"],
                name=team_data["name"],
                key=team_data["key"]
            )
            teams.append(team)
        
        return teams
    
    async def create_issue(
        self,
        title: str,
        team_id: str,
        description: Optional[str] = None,
        priority: IssuePriority = IssuePriority.MEDIUM
    ) -> LinearIssue:
        """Create a new issue"""
        query = gql("""
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        title
                        description
                        state {
                            name
                        }
                        priority
                        url
                        identifier
                        team {
                            id
                        }
                        createdAt
                        updatedAt
                    }
                }
            }
        """)
        
        variables = {
            "input": {
                "title": title,
                "teamId": team_id,
                "description": description,
                "priority": priority.value
            }
        }
        
        result = await self._execute_with_retry(query, variables)
        
        if not result["issueCreate"]["success"]:
            raise Exception("Failed to create issue")
        
        issue_data = result["issueCreate"]["issue"]
        
        # Map state name to enum
        state_map = {
            "Backlog": IssueState.BACKLOG,
            "Todo": IssueState.UNSTARTED,
            "In Progress": IssueState.STARTED,
            "Done": IssueState.COMPLETED,
            "Canceled": IssueState.CANCELED
        }
        
        state = state_map.get(issue_data["state"]["name"], IssueState.BACKLOG)
        
        issue = LinearIssue(
            id=issue_data["id"],
            title=issue_data["title"],
            description=issue_data.get("description"),
            state=state,
            priority=IssuePriority(issue_data["priority"]),
            url=issue_data["url"],
            identifier=issue_data["identifier"],
            team_id=issue_data["team"]["id"],
            created_at=issue_data["createdAt"],
            updated_at=issue_data["updatedAt"]
        )
        
        logger.info(f"Created issue: {issue.identifier} - {issue.title}")
        return issue
    
    async def get_issue(self, issue_id: str) -> Optional[LinearIssue]:
        """Get issue by ID"""
        query = gql("""
            query GetIssue($id: String!) {
                issue(id: $id) {
                    id
                    title
                    description
                    state {
                        name
                    }
                    priority
                    url
                    identifier
                    team {
                        id
                    }
                    createdAt
                    updatedAt
                }
            }
        """)
        
        variables = {"id": issue_id}
        result = await self._execute_with_retry(query, variables)
        
        if not result["issue"]:
            return None
        
        issue_data = result["issue"]
        
        # Map state name to enum
        state_map = {
            "Backlog": IssueState.BACKLOG,
            "Todo": IssueState.UNSTARTED,
            "In Progress": IssueState.STARTED,
            "Done": IssueState.COMPLETED,
            "Canceled": IssueState.CANCELED
        }
        
        state = state_map.get(issue_data["state"]["name"], IssueState.BACKLOG)
        
        return LinearIssue(
            id=issue_data["id"],
            title=issue_data["title"],
            description=issue_data.get("description"),
            state=state,
            priority=IssuePriority(issue_data["priority"]),
            url=issue_data["url"],
            identifier=issue_data["identifier"],
            team_id=issue_data["team"]["id"],
            created_at=issue_data["createdAt"],
            updated_at=issue_data["updatedAt"]
        )
    
    async def update_issue(
        self,
        issue_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        state: Optional[IssueState] = None,
        priority: Optional[IssuePriority] = None
    ) -> LinearIssue:
        """Update an existing issue"""
        
        # Build update input
        update_input = {"id": issue_id}
        
        if title is not None:
            update_input["title"] = title
        
        if description is not None:
            update_input["description"] = description
        
        if priority is not None:
            update_input["priority"] = priority.value
        
        # For state updates, we need to use a different mutation
        if state is not None:
            # This is a simplified approach - in production you'd need to map states to proper state IDs
            logger.warning("State updates not fully implemented - requires state ID mapping")
        
        query = gql("""
            mutation UpdateIssue($input: IssueUpdateInput!) {
                issueUpdate(input: $input) {
                    success
                    issue {
                        id
                        title
                        description
                        state {
                            name
                        }
                        priority
                        url
                        identifier
                        team {
                            id
                        }
                        createdAt
                        updatedAt
                    }
                }
            }
        """)
        
        variables = {"input": update_input}
        result = await self._execute_with_retry(query, variables)
        
        if not result["issueUpdate"]["success"]:
            raise Exception("Failed to update issue")
        
        issue_data = result["issueUpdate"]["issue"]
        
        # Map state name to enum
        state_map = {
            "Backlog": IssueState.BACKLOG,
            "Todo": IssueState.UNSTARTED,
            "In Progress": IssueState.STARTED,
            "Done": IssueState.COMPLETED,
            "Canceled": IssueState.CANCELED
        }
        
        state_enum = state_map.get(issue_data["state"]["name"], IssueState.BACKLOG)
        
        issue = LinearIssue(
            id=issue_data["id"],
            title=issue_data["title"],
            description=issue_data.get("description"),
            state=state_enum,
            priority=IssuePriority(issue_data["priority"]),
            url=issue_data["url"],
            identifier=issue_data["identifier"],
            team_id=issue_data["team"]["id"],
            created_at=issue_data["createdAt"],
            updated_at=issue_data["updatedAt"]
        )
        
        logger.info(f"Updated issue: {issue.identifier}")
        return issue
    
    async def health_check(self) -> bool:
        """Check if Linear API is accessible"""
        try:
            await self.get_teams()
            return True
        except Exception as e:
            logger.error(f"Linear health check failed: {e}")
            return False