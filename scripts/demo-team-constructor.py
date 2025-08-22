"""
Team Constructor Demo - TEAM-02 functionality for ATLAS Phase 4

Demonstrates dynamic team formation based on task requirements.
Shows how the Team Constructor integrates with the Agent Registry.
"""

import asyncio
import logging
from agents.registry import AgentRegistry, CapabilityMatcher, HealthMonitor, LoadBalancer, TeamConstructor
from agents.registry.capability_matcher import TaskRequirement

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_team_constructor():
    """Demonstrate Team Constructor functionality"""
    logger.info("🚀 Starting Team Constructor Demo...")
    
    # Initialize components
    registry = AgentRegistry("./config/agents.json")
    await registry.initialize()
    
    capability_matcher = CapabilityMatcher()
    health_monitor = HealthMonitor(registry)
    load_balancer = LoadBalancer(registry, capability_matcher)
    team_constructor = TeamConstructor(registry, capability_matcher, load_balancer)
    
    # Start health monitoring (this will set agents to healthy status)
    await health_monitor.start_monitoring()
    
    # Wait for initial health check to complete
    await asyncio.sleep(1)
    
    logger.info("✅ All components initialized")
    
    try:
        # Demonstrate different team formation scenarios
        await demo_simple_task(team_constructor)
        await demo_complex_task(team_constructor)
        await demo_security_focused_task(team_constructor)
        await demo_custom_requirements(team_constructor)
        
        # Show statistics
        stats = team_constructor.get_formation_statistics()
        logger.info(f"\n📊 Team Formation Statistics:")
        for key, value in stats.items():
            logger.info(f"  • {key}: {value}")
        
        # List active teams
        active_teams = team_constructor.list_active_teams()
        logger.info(f"\n👥 Active Teams: {len(active_teams)}")
        
        # Clean up teams
        for team in active_teams:
            await team_constructor.disband_team(team.team_id)
        
    finally:
        await health_monitor.stop_monitoring()


async def demo_simple_task(team_constructor: TeamConstructor):
    """Demo simple task team formation"""
    logger.info("\n📝 Demo 1: Simple User Interface Task")
    
    task = "Create a user-friendly interface for displaying search results"
    team = await team_constructor.form_team(task)
    
    if team:
        logger.info(f"✅ Team formed: {team.team_id}")
        logger.info(f"Formation time: {team.formation_time:.2f}s")
        
        suggestions = await team_constructor.suggest_team_improvements(team.team_id)
        logger.info(f"Suggestions: {suggestions}")
    else:
        logger.warning("❌ Failed to form team")


async def demo_complex_task(team_constructor: TeamConstructor):
    """Demo complex multi-capability task"""
    logger.info("\n🔧 Demo 2: Complex Orchestration Task")
    
    task = "Orchestrate a complex workflow that involves user interface, data processing, tool integration, and Linear issue management"
    team = await team_constructor.form_team(task)
    
    if team:
        logger.info(f"✅ Team formed: {team.team_id}")
        logger.info(f"Formation time: {team.formation_time:.2f}s")
        logger.info(f"Coordinator: {team.coordinator_agent_id}")
        
        # Show detailed team composition
        logger.info("Team composition:")
        for member in team.members:
            logger.info(f"  • {member.role}: {member.agent.name}")
            logger.info(f"    Load: {member.load_allocation:.1f}")
    else:
        logger.warning("❌ Failed to form team")


async def demo_security_focused_task(team_constructor: TeamConstructor):
    """Demo security-focused task"""
    logger.info("\n🔒 Demo 3: Security Monitoring Task")
    
    task = "Monitor system security, check compliance, and respond to any security incidents"
    team = await team_constructor.form_team(task)
    
    if team:
        logger.info(f"✅ Team formed: {team.team_id}")
        
        # Check if security capabilities are properly assigned
        security_members = [
            m for m in team.members 
            if any(cap.startswith("security") or cap.startswith("compliance") 
                   for cap in m.capabilities_assigned)
        ]
        logger.info(f"Security specialists in team: {len(security_members)}")
    else:
        logger.warning("❌ Failed to form team")


async def demo_custom_requirements(team_constructor: TeamConstructor):
    """Demo with custom requirements"""
    logger.info("\n⚙️ Demo 4: Custom Requirements")
    
    # Define specific requirements
    custom_requirements = [
        TaskRequirement(capability="task_orchestration", required=True, priority=5),
        TaskRequirement(capability="mcp_integration", required=True, priority=4),
        TaskRequirement(capability="linear_integration", required=True, priority=4),
        TaskRequirement(capability="security_monitoring", required=False, priority=2)
    ]
    
    task = "Custom task with specific capability requirements"
    team = await team_constructor.form_team(task, custom_requirements=custom_requirements)
    
    if team:
        logger.info(f"✅ Team formed: {team.team_id}")
        
        # Verify requirements are met
        all_capabilities = set()
        for member in team.members:
            all_capabilities.update(member.capabilities_assigned)
        
        required_caps = [req.capability for req in custom_requirements if req.required]
        missing_caps = [cap for cap in required_caps if cap not in all_capabilities]
        
        if missing_caps:
            logger.warning(f"Missing required capabilities: {missing_caps}")
        else:
            logger.info("✅ All required capabilities covered")
    else:
        logger.warning("❌ Failed to form team")


if __name__ == "__main__":
    asyncio.run(demonstrate_team_constructor())