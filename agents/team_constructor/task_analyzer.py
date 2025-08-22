"""
Task Analyzer

Analyze incoming tasks to determine required capabilities and team requirements.
"""

import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"  
    COMPLEX = "complex"
    EXPERT = "expert"


class TaskType(Enum):
    """Task type categories"""
    ANALYSIS = "analysis"
    GENERATION = "generation"
    RESEARCH = "research"
    CODING = "coding"
    AUTOMATION = "automation"
    COORDINATION = "coordination"
    MONITORING = "monitoring"
    GENERAL = "general"


@dataclass
class TaskRequirement:
    """Task requirement specification"""
    capability: str
    priority: int = 1  # 1=critical, 2=important, 3=nice-to-have
    parameters: Dict = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class TaskAnalysis:
    """Task analysis result"""
    task_id: str
    complexity: TaskComplexity
    task_type: TaskType
    estimated_duration_minutes: int
    required_capabilities: List[TaskRequirement]
    suggested_team_size: int
    special_requirements: List[str]
    confidence_score: float


class TaskAnalyzer:
    """Analyze tasks to determine team requirements"""
    
    def __init__(self):
        # Capability patterns for text analysis
        self.capability_patterns = {
            "coding": [
                r"\b(?:code|program|script|implement|develop|debug)\b",
                r"\b(?:python|javascript|api|function|class|method)\b"
            ],
            "analysis": [
                r"\b(?:analyz|examine|evaluat|assess|review|investigat)\b",
                r"\b(?:data|information|results|findings|report)\b"
            ],
            "research": [
                r"\b(?:research|search|find|discover|gather|collect)\b",
                r"\b(?:information|sources|references|documentation)\b"
            ],
            "automation": [
                r"\b(?:automat|schedul|trigger|workflow|process|batch)\b",
                r"\b(?:script|bot|scheduler|cron|pipeline)\b"
            ],
            "monitoring": [
                r"\b(?:monitor|track|watch|alert|observe|surveillance)\b",
                r"\b(?:health|status|metrics|logs|events)\b"
            ],
            "coordination": [
                r"\b(?:coordinat|orchestrat|manag|organiz|synchroniz)\b",
                r"\b(?:team|group|agents|workflow|tasks)\b"
            ]
        }
        
        # Complexity indicators
        self.complexity_indicators = {
            TaskComplexity.SIMPLE: [
                r"\b(?:simple|basic|quick|easy|straightforward)\b",
                r"\b(?:single|one|simple)\s+(?:task|action|step)\b"
            ],
            TaskComplexity.MODERATE: [
                r"\b(?:multiple|several|few|some)\s+(?:steps|tasks|actions)\b",
                r"\b(?:moderate|medium|standard|regular)\b"
            ],
            TaskComplexity.COMPLEX: [
                r"\b(?:complex|complicated|advanced|detailed|comprehensive)\b",
                r"\b(?:many|numerous|extensive|multiple)\s+(?:components|parts|steps)\b"
            ],
            TaskComplexity.EXPERT: [
                r"\b(?:expert|specialist|advanced|critical|mission-critical)\b",
                r"\b(?:enterprise|production|large-scale|high-availability)\b"
            ]
        }
        
    async def analyze_task(self, task_description: str, task_id: str = None) -> TaskAnalysis:
        """Analyze a task description to determine requirements"""
        if task_id is None:
            task_id = f"task_{hash(task_description) % 10000}"
            
        # Determine task type and complexity
        task_type = await self._classify_task_type(task_description)
        complexity = await self._assess_complexity(task_description)
        
        # Extract required capabilities
        required_capabilities = await self._extract_capabilities(task_description)
        
        # Estimate duration and team size
        duration = await self._estimate_duration(task_description, complexity)
        team_size = await self._suggest_team_size(complexity, required_capabilities)
        
        # Extract special requirements
        special_requirements = await self._extract_special_requirements(task_description)
        
        # Calculate confidence score
        confidence = await self._calculate_confidence(task_description, required_capabilities)
        
        return TaskAnalysis(
            task_id=task_id,
            complexity=complexity,
            task_type=task_type,
            estimated_duration_minutes=duration,
            required_capabilities=required_capabilities,
            suggested_team_size=team_size,
            special_requirements=special_requirements,
            confidence_score=confidence
        )
        
    async def _classify_task_type(self, description: str) -> TaskType:
        """Classify the type of task"""
        text = description.lower()
        
        # Score each task type
        type_scores = {}
        for task_type in TaskType:
            score = 0
            patterns = self.capability_patterns.get(task_type.value, [])
            
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
                
            type_scores[task_type] = score
            
        # Return the highest scoring type, or GENERAL if no clear match
        best_type = max(type_scores.items(), key=lambda x: x[1])
        return best_type[0] if best_type[1] > 0 else TaskType.GENERAL
        
    async def _assess_complexity(self, description: str) -> TaskComplexity:
        """Assess task complexity"""
        text = description.lower()
        
        # Score each complexity level
        complexity_scores = {}
        for complexity in TaskComplexity:
            score = 0
            patterns = self.complexity_indicators.get(complexity, [])
            
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
                
            complexity_scores[complexity] = score
            
        # Consider text length as a complexity factor
        word_count = len(text.split())
        if word_count > 100:
            complexity_scores[TaskComplexity.COMPLEX] += 2
        elif word_count > 50:
            complexity_scores[TaskComplexity.MODERATE] += 1
            
        # Return highest scoring complexity, default to MODERATE
        best_complexity = max(complexity_scores.items(), key=lambda x: x[1])
        return best_complexity[0] if best_complexity[1] > 0 else TaskComplexity.MODERATE
        
    async def _extract_capabilities(self, description: str) -> List[TaskRequirement]:
        """Extract required capabilities from task description"""
        text = description.lower()
        requirements = []
        
        # Check for each capability pattern
        for capability, patterns in self.capability_patterns.items():
            score = 0
            for pattern in patterns:
                score += len(re.findall(pattern, text, re.IGNORECASE))
                
            if score > 0:
                # Determine priority based on score
                if score >= 3:
                    priority = 1  # Critical
                elif score >= 2:
                    priority = 2  # Important
                else:
                    priority = 3  # Nice-to-have
                    
                requirements.append(TaskRequirement(
                    capability=capability,
                    priority=priority
                ))
                
        # If no specific capabilities found, add general capability
        if not requirements:
            requirements.append(TaskRequirement(
                capability="general",
                priority=2
            ))
            
        return requirements
        
    async def _estimate_duration(self, description: str, complexity: TaskComplexity) -> int:
        """Estimate task duration in minutes"""
        word_count = len(description.split())
        
        # Base time estimates by complexity
        base_times = {
            TaskComplexity.SIMPLE: 15,
            TaskComplexity.MODERATE: 45,
            TaskComplexity.COMPLEX: 120,
            TaskComplexity.EXPERT: 300
        }
        
        base_time = base_times.get(complexity, 45)
        
        # Adjust based on description length
        length_multiplier = min(1 + (word_count / 100), 3.0)
        
        return int(base_time * length_multiplier)
        
    async def _suggest_team_size(
        self, 
        complexity: TaskComplexity, 
        capabilities: List[TaskRequirement]
    ) -> int:
        """Suggest optimal team size"""
        
        # Base team size by complexity
        base_sizes = {
            TaskComplexity.SIMPLE: 1,
            TaskComplexity.MODERATE: 2,
            TaskComplexity.COMPLEX: 3,
            TaskComplexity.EXPERT: 4
        }
        
        base_size = base_sizes.get(complexity, 2)
        
        # Adjust based on number of critical capabilities
        critical_caps = len([c for c in capabilities if c.priority == 1])
        size_adjustment = min(critical_caps, 2)  # Max +2 for critical capabilities
        
        return min(base_size + size_adjustment, 5)  # Cap at 5 agents
        
    async def _extract_special_requirements(self, description: str) -> List[str]:
        """Extract special requirements from description"""
        text = description.lower()
        special_requirements = []
        
        # Check for common special requirements
        if re.search(r"\b(?:urgent|immediate|asap|priority|critical)\b", text):
            special_requirements.append("high_priority")
            
        if re.search(r"\b(?:secure|security|private|confidential)\b", text):
            special_requirements.append("security_clearance")
            
        if re.search(r"\b(?:real.?time|live|streaming|continuous)\b", text):
            special_requirements.append("real_time")
            
        if re.search(r"\b(?:24/7|always.?on|continuous|persistent)\b", text):
            special_requirements.append("continuous_operation")
            
        return special_requirements
        
    async def _calculate_confidence(
        self, 
        description: str, 
        capabilities: List[TaskRequirement]
    ) -> float:
        """Calculate confidence score for the analysis"""
        
        # Base confidence from description length and structure
        word_count = len(description.split())
        if word_count < 5:
            base_confidence = 0.3
        elif word_count < 20:
            base_confidence = 0.6
        else:
            base_confidence = 0.8
            
        # Boost confidence if we found specific capabilities
        if capabilities and any(c.capability != "general" for c in capabilities):
            base_confidence += 0.2
            
        return min(base_confidence, 1.0)