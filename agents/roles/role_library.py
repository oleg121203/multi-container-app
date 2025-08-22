"""
Role Library - Standard role definitions for ATLAS Phase 4

Provides a comprehensive library of predefined agent roles.
Includes common patterns for coordinators, specialists, analysts, and more.
"""

import logging
from typing import Dict, List, Optional, Any
from agents.roles.role_template import (
    RoleTemplate, RoleCategory, BehaviorPattern, RoleConstraint, RoleMetrics,
    CommunicationStyle, DecisionMakingStyle
)

logger = logging.getLogger(__name__)


class RoleLibrary:
    """
    Library of predefined role templates
    
    Provides standard role definitions for common agent types and patterns.
    Supports role inheritance and customization.
    """
    
    def __init__(self):
        """Initialize the role library with standard templates"""
        self.templates: Dict[str, RoleTemplate] = {}
        self._initialize_standard_roles()
        
        logger.info(f"RoleLibrary initialized with {len(self.templates)} standard roles")

    def _initialize_standard_roles(self) -> None:
        """Initialize standard role templates"""
        
        # Base Coordinator Role
        coordinator = RoleTemplate(
            role_id="coordinator",
            name="Team Coordinator",
            description="Manages team coordination and task distribution",
            category=RoleCategory.COORDINATOR,
            required_capabilities=["task_orchestration", "team_management"],
            preferred_capabilities=["communication", "planning"],
            communication_style=CommunicationStyle.COLLABORATIVE,
            decision_making_style=DecisionMakingStyle.CONSULTATIVE,
            behavior_patterns=[
                BehaviorPattern(
                    pattern_id="coordinate_tasks",
                    name="Task Coordination",
                    description="Coordinate tasks among team members",
                    triggers=["task_assignment_needed", "team_formation"],
                    actions=["analyze_requirements", "assign_tasks", "monitor_progress"],
                    priority=10
                ),
                BehaviorPattern(
                    pattern_id="conflict_resolution",
                    name="Conflict Resolution",
                    description="Resolve conflicts between team members",
                    triggers=["conflict_detected", "disagreement"],
                    actions=["mediate_discussion", "find_compromise", "escalate_if_needed"],
                    priority=8
                )
            ],
            interaction_rules={
                "team_meeting": "Facilitate discussion and ensure all voices are heard",
                "task_assignment": "Consider individual strengths and workload balance",
                "conflict": "Remain neutral and focus on finding solutions"
            },
            response_templates={
                "task_assignment": "I'm assigning {task} to {agent} based on their {capability} expertise.",
                "progress_check": "Let's review our progress on {task}. {agent}, can you provide an update?",
                "conflict_resolution": "I understand there's a disagreement about {topic}. Let's discuss the different perspectives."
            },
            permissions=["assign_tasks", "modify_team_composition", "escalate_issues"],
            success_criteria=[
                "Team tasks completed on time",
                "High team satisfaction scores",
                "Minimal unresolved conflicts"
            ]
        )
        
        # Security Specialist Role
        security_specialist = RoleTemplate(
            role_id="security_specialist",
            name="Security Specialist",
            description="Focuses on security monitoring and threat analysis",
            category=RoleCategory.SPECIALIST,
            required_capabilities=["security_monitoring", "threat_analysis"],
            preferred_capabilities=["compliance_checking", "risk_assessment"],
            communication_style=CommunicationStyle.TECHNICAL,
            decision_making_style=DecisionMakingStyle.DATA_DRIVEN,
            behavior_patterns=[
                BehaviorPattern(
                    pattern_id="threat_detection",
                    name="Threat Detection",
                    description="Monitor for security threats and vulnerabilities",
                    triggers=["security_scan", "suspicious_activity"],
                    actions=["analyze_threat", "assess_risk", "recommend_action"],
                    priority=10
                ),
                BehaviorPattern(
                    pattern_id="compliance_check",
                    name="Compliance Verification",
                    description="Verify compliance with security policies",
                    triggers=["policy_check", "audit_request"],
                    actions=["review_policies", "check_compliance", "report_violations"],
                    priority=7
                )
            ],
            interaction_rules={
                "threat_alert": "Immediately notify relevant stakeholders of security threats",
                "compliance_review": "Provide detailed analysis with actionable recommendations",
                "security_briefing": "Present findings in clear, prioritized manner"
            },
            response_templates={
                "threat_detected": "Security threat detected: {threat_type}. Risk level: {risk_level}. Recommended action: {action}",
                "compliance_status": "Compliance check for {policy}: {status}. {details}",
                "security_recommendation": "Based on analysis, I recommend: {recommendation}"
            },
            constraints=[
                RoleConstraint(
                    constraint_id="data_access",
                    constraint_type="permission",
                    description="Limited to security-related data access",
                    rules=["Can access security logs and monitoring data", "Cannot access personal user data without authorization"]
                )
            ],
            permissions=["access_security_logs", "initiate_security_scans", "escalate_threats"],
            success_criteria=[
                "Zero undetected security incidents",
                "100% compliance with security policies",
                "Rapid threat response times"
            ]
        )
        
        # Data Analyst Role
        data_analyst = RoleTemplate(
            role_id="data_analyst",
            name="Data Analyst",
            description="Analyzes data and provides insights for decision making",
            category=RoleCategory.ANALYST,
            required_capabilities=["data_analysis", "statistical_analysis"],
            preferred_capabilities=["visualization", "machine_learning"],
            communication_style=CommunicationStyle.ANALYTICAL,
            decision_making_style=DecisionMakingStyle.DATA_DRIVEN,
            behavior_patterns=[
                BehaviorPattern(
                    pattern_id="data_exploration",
                    name="Data Exploration",
                    description="Explore and understand data patterns",
                    triggers=["data_analysis_request", "new_dataset"],
                    actions=["examine_data_quality", "identify_patterns", "generate_hypotheses"],
                    priority=10
                ),
                BehaviorPattern(
                    pattern_id="insight_generation",
                    name="Insight Generation",
                    description="Generate actionable insights from analysis",
                    triggers=["analysis_complete", "pattern_identified"],
                    actions=["synthesize_findings", "create_visualizations", "recommend_actions"],
                    priority=9
                )
            ],
            interaction_rules={
                "data_request": "Clarify requirements and expected outcomes before starting analysis",
                "results_presentation": "Present findings with context and limitations",
                "follow_up": "Offer to dive deeper into specific areas of interest"
            },
            response_templates={
                "analysis_start": "Beginning analysis of {dataset} to address {question}. Expected completion: {timeline}",
                "insight_found": "Analysis reveals: {insight}. Confidence level: {confidence}. Recommendation: {recommendation}",
                "clarification_needed": "To provide accurate analysis, I need clarification on: {requirements}"
            },
            permissions=["access_analytical_data", "generate_reports", "create_visualizations"],
            success_criteria=[
                "Insights lead to improved decision making",
                "High accuracy of predictions and recommendations",
                "Stakeholder satisfaction with analysis quality"
            ]
        )
        
        # UI/UX Specialist Role
        ui_specialist = RoleTemplate(
            role_id="ui_specialist",
            name="UI/UX Specialist",
            description="Focuses on user interface design and user experience",
            category=RoleCategory.SPECIALIST,
            required_capabilities=["user_interface", "user_experience"],
            preferred_capabilities=["design_principles", "accessibility"],
            communication_style=CommunicationStyle.SUPPORTIVE,
            decision_making_style=DecisionMakingStyle.CONSULTATIVE,
            behavior_patterns=[
                BehaviorPattern(
                    pattern_id="user_centered_design",
                    name="User-Centered Design",
                    description="Focus on user needs in design decisions",
                    triggers=["design_request", "user_feedback"],
                    actions=["analyze_user_needs", "create_prototypes", "test_usability"],
                    priority=10
                ),
                BehaviorPattern(
                    pattern_id="accessibility_review",
                    name="Accessibility Review",
                    description="Ensure designs are accessible to all users",
                    triggers=["design_review", "accessibility_check"],
                    actions=["review_accessibility", "suggest_improvements", "validate_compliance"],
                    priority=8
                )
            ],
            interaction_rules={
                "design_feedback": "Provide constructive feedback focused on user experience",
                "stakeholder_review": "Explain design decisions in terms of user benefits",
                "iteration": "Embrace iterative design and continuous improvement"
            },
            response_templates={
                "design_proposal": "Here's a design that addresses {user_need} by {solution}. Key benefits: {benefits}",
                "usability_concern": "I've identified a usability issue: {issue}. Suggested fix: {fix}",
                "accessibility_note": "To improve accessibility, consider: {recommendation}"
            },
            permissions=["create_designs", "conduct_user_research", "modify_interfaces"],
            success_criteria=[
                "High user satisfaction scores",
                "Improved usability metrics",
                "Accessibility compliance achieved"
            ]
        )
        
        # Creative Thinker Role
        creative_thinker = RoleTemplate(
            role_id="creative_thinker",
            name="Creative Thinker",
            description="Generates innovative ideas and creative solutions",
            category=RoleCategory.CREATIVE,
            required_capabilities=["creative_thinking", "problem_solving"],
            preferred_capabilities=["brainstorming", "innovation"],
            communication_style=CommunicationStyle.CASUAL,
            decision_making_style=DecisionMakingStyle.INTUITIVE,
            behavior_patterns=[
                BehaviorPattern(
                    pattern_id="ideation",
                    name="Idea Generation",
                    description="Generate creative ideas and solutions",
                    triggers=["brainstorming_session", "problem_to_solve"],
                    actions=["think_outside_box", "combine_concepts", "explore_alternatives"],
                    priority=10
                ),
                BehaviorPattern(
                    pattern_id="creative_synthesis",
                    name="Creative Synthesis",
                    description="Combine different ideas into innovative solutions",
                    triggers=["multiple_ideas_available", "synthesis_needed"],
                    actions=["identify_connections", "merge_concepts", "refine_solutions"],
                    priority=8
                )
            ],
            interaction_rules={
                "brainstorming": "Encourage wild ideas and build on others' suggestions",
                "critique": "Focus on improving ideas rather than rejecting them",
                "presentation": "Make ideas tangible with examples and stories"
            },
            response_templates={
                "new_idea": "What if we tried {idea}? This could {benefit} by {mechanism}",
                "build_on_idea": "Building on {previous_idea}, we could also {extension}",
                "creative_solution": "Here's a creative approach: {solution}. It's unconventional but could work because {reasoning}"
            },
            permissions=["propose_new_approaches", "challenge_assumptions", "experiment_with_ideas"],
            success_criteria=[
                "Generated ideas lead to successful implementations",
                "High creativity ratings from stakeholders",
                "Breakthrough solutions to difficult problems"
            ]
        )
        
        # Technical Validator Role
        validator = RoleTemplate(
            role_id="technical_validator",
            name="Technical Validator", 
            description="Reviews and validates technical work and decisions",
            category=RoleCategory.VALIDATOR,
            required_capabilities=["technical_review", "quality_assurance"],
            preferred_capabilities=["testing", "documentation"],
            communication_style=CommunicationStyle.TECHNICAL,
            decision_making_style=DecisionMakingStyle.DATA_DRIVEN,
            behavior_patterns=[
                BehaviorPattern(
                    pattern_id="technical_review",
                    name="Technical Review",
                    description="Conduct thorough technical reviews",
                    triggers=["review_request", "code_submission"],
                    actions=["analyze_technical_quality", "check_standards", "identify_issues"],
                    priority=10
                ),
                BehaviorPattern(
                    pattern_id="quality_assurance",
                    name="Quality Assurance",
                    description="Ensure quality standards are met",
                    triggers=["qa_check", "deployment_ready"],
                    actions=["run_tests", "verify_requirements", "validate_performance"],
                    priority=9
                )
            ],
            interaction_rules={
                "feedback": "Provide specific, actionable feedback with examples",
                "approval": "Only approve work that meets all quality criteria", 
                "mentoring": "Help others understand quality standards and best practices"
            },
            response_templates={
                "review_feedback": "Technical review complete. Issues found: {issues}. Strengths: {strengths}. Next steps: {actions}",
                "quality_check": "Quality assessment: {status}. {details}",
                "approval": "Technical validation complete. {component} meets all requirements and is approved for {next_stage}"
            },
            constraints=[
                RoleConstraint(
                    constraint_id="quality_standards",
                    constraint_type="permission", 
                    description="Must enforce quality standards consistently",
                    rules=["Cannot approve substandard work", "Must document all review decisions"]
                )
            ],
            permissions=["block_low_quality_work", "require_revisions", "set_quality_standards"],
            success_criteria=[
                "Zero quality issues in approved work",
                "Consistent application of standards",
                "Improved overall team quality metrics"
            ]
        )
        
        # Store all templates
        self.templates = {
            "coordinator": coordinator,
            "security_specialist": security_specialist,
            "data_analyst": data_analyst,
            "ui_specialist": ui_specialist,
            "creative_thinker": creative_thinker,
            "technical_validator": validator
        }

    def get_role_template(self, role_id: str) -> Optional[RoleTemplate]:
        """Get a specific role template by ID"""
        return self.templates.get(role_id)

    def list_roles(self, category: Optional[RoleCategory] = None) -> List[RoleTemplate]:
        """List all available role templates, optionally filtered by category"""
        if category:
            return [
                template for template in self.templates.values()
                if template.category == category
            ]
        return list(self.templates.values())

    def add_role_template(self, template: RoleTemplate) -> bool:
        """Add a new role template to the library"""
        if template.role_id in self.templates:
            logger.warning(f"Role template {template.role_id} already exists")
            return False
        
        # Validate template
        issues = template.validate_role_consistency()
        if issues:
            logger.error(f"Role template validation failed: {issues}")
            return False
        
        self.templates[template.role_id] = template
        logger.info(f"Added role template: {template.role_id}")
        return True

    def update_role_template(self, template: RoleTemplate) -> bool:
        """Update an existing role template"""
        if template.role_id not in self.templates:
            logger.warning(f"Role template {template.role_id} not found")
            return False
        
        # Validate template
        issues = template.validate_role_consistency()
        if issues:
            logger.error(f"Role template validation failed: {issues}")
            return False
        
        self.templates[template.role_id] = template
        logger.info(f"Updated role template: {template.role_id}")
        return True

    def remove_role_template(self, role_id: str) -> bool:
        """Remove a role template from the library"""
        if role_id not in self.templates:
            return False
        
        del self.templates[role_id]
        logger.info(f"Removed role template: {role_id}")
        return True

    def find_compatible_roles(
        self,
        agent_capabilities: List[str],
        min_compatibility: float = 0.5
    ) -> List[tuple[RoleTemplate, float]]:
        """Find roles compatible with given agent capabilities"""
        compatible_roles = []
        
        for template in self.templates.values():
            if not template.is_active:
                continue
                
            compatibility = template.calculate_compatibility_score(agent_capabilities)
            if compatibility >= min_compatibility:
                compatible_roles.append((template, compatibility))
        
        # Sort by compatibility score (highest first)
        compatible_roles.sort(key=lambda x: x[1], reverse=True)
        return compatible_roles

    def get_roles_by_category(self, category: RoleCategory) -> List[RoleTemplate]:
        """Get all roles in a specific category"""
        return [
            template for template in self.templates.values()
            if template.category == category and template.is_active
        ]

    def search_roles(
        self,
        query: str,
        search_fields: Optional[List[str]] = None
    ) -> List[RoleTemplate]:
        """Search for roles by name, description, or capabilities"""
        if search_fields is None:
            search_fields = ["name", "description", "required_capabilities", "preferred_capabilities"]
        
        query_lower = query.lower()
        matching_roles = []
        
        for template in self.templates.values():
            if not template.is_active:
                continue
                
            # Check each search field
            for field in search_fields:
                if field == "name" and query_lower in template.name.lower():
                    matching_roles.append(template)
                    break
                elif field == "description" and query_lower in template.description.lower():
                    matching_roles.append(template)
                    break
                elif field == "required_capabilities":
                    if any(query_lower in cap.lower() for cap in template.required_capabilities):
                        matching_roles.append(template)
                        break
                elif field == "preferred_capabilities":
                    if any(query_lower in cap.lower() for cap in template.preferred_capabilities):
                        matching_roles.append(template)
                        break
        
        return matching_roles

    def create_role_hierarchy(self) -> Dict[str, List[str]]:
        """Create a hierarchy map of parent-child relationships"""
        hierarchy = {}
        
        for template in self.templates.values():
            # Initialize entry
            if template.role_id not in hierarchy:
                hierarchy[template.role_id] = []
            
            # Add children
            for child_role in template.child_roles:
                if child_role in self.templates:
                    hierarchy[template.role_id].append(child_role)
            
            # Ensure parent entries exist
            for parent_role in template.parent_roles:
                if parent_role not in hierarchy:
                    hierarchy[parent_role] = []
                if template.role_id not in hierarchy[parent_role]:
                    hierarchy[parent_role].append(template.role_id)
        
        return hierarchy

    def get_role_statistics(self) -> Dict[str, Any]:
        """Get statistics about the role library"""
        if not self.templates:
            return {}
        
        total_roles = len(self.templates)
        active_roles = sum(1 for t in self.templates.values() if t.is_active)
        
        # Count by category
        category_counts = {}
        for template in self.templates.values():
            category = template.category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count communication styles
        comm_style_counts = {}
        for template in self.templates.values():
            style = template.communication_style
            comm_style_counts[style] = comm_style_counts.get(style, 0) + 1
        
        # Capability usage
        all_capabilities = set()
        for template in self.templates.values():
            all_capabilities.update(template.required_capabilities)
            all_capabilities.update(template.preferred_capabilities)
        
        return {
            "total_roles": total_roles,
            "active_roles": active_roles,
            "category_distribution": category_counts,
            "communication_style_distribution": comm_style_counts,
            "unique_capabilities": len(all_capabilities),
            "most_common_capabilities": list(all_capabilities)[:10]  # Top 10
        }