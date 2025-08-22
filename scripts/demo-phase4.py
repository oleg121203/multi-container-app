"""
Phase 4 Agent Registry Integration Example

Demonstrates how the new Agent Registry integrates with existing ATLAS components
and provides dynamic team formation capabilities.
"""

import asyncio
import logging
from typing import List

from agents.registry.agent_registry import AgentRegistry, AgentStatus
from agents.registry.capability_matcher import CapabilityMatcher, TaskRequirement
from agents.registry.health_monitor import HealthMonitor
from agents.registry.load_balancer import LoadBalancer, LoadBalancingStrategy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Phase4Demo:
    """Demo class showing Phase 4 Agent Registry functionality"""
    
    def __init__(self):
        self.registry = None
        self.capability_matcher = None
        self.health_monitor = None
        self.load_balancer = None
    
    async def initialize(self):
        """Initialize all Phase 4 components"""
        logger.info("🚀 Initializing Phase 4 Agent Registry System...")
        
        # Initialize Agent Registry
        self.registry = AgentRegistry("./config/agents.json")
        await self.registry.initialize()
        logger.info(f"✅ Agent Registry initialized with {len(self.registry.agents)} agents")
        
        # Initialize Capability Matcher
        self.capability_matcher = CapabilityMatcher()
        logger.info("✅ Capability Matcher initialized")
        
        # Initialize Health Monitor
        self.health_monitor = HealthMonitor(self.registry)
        logger.info("✅ Health Monitor initialized")
        
        # Initialize Load Balancer
        self.load_balancer = LoadBalancer(self.registry, self.capability_matcher)
        logger.info("✅ Load Balancer initialized")
        
        # Start health monitoring
        await self.health_monitor.start_monitoring()
        logger.info("✅ Health monitoring started")
    
    async def demonstrate_agent_discovery(self):
        """Demonstrate agent discovery and capability lookup"""
        logger.info("\n📋 Demonstrating Agent Discovery...")
        
        # List all agents
        agents = await self.registry.list_agents()
        logger.info(f"Total registered agents: {len(agents)}")
        
        for agent in agents:
            capabilities = [cap.name for cap in agent.capabilities]
            logger.info(f"  • {agent.name} ({agent.agent_id}): {capabilities}")
        
        # Show capability index
        logger.info(f"\nCapability Index: {list(self.registry.capabilities_index.keys())}")
        
        # Find agents by specific capabilities
        ui_agents = await self.registry.get_agents_by_capability("user_interface")
        logger.info(f"Agents with UI capability: {[a.name for a in ui_agents]}")
        
        orchestration_agents = await self.registry.get_agents_by_capability("task_orchestration")
        logger.info(f"Agents with orchestration capability: {[a.name for a in orchestration_agents]}")
    
    async def demonstrate_dynamic_team_formation(self):
        """Demonstrate dynamic team formation based on task requirements"""
        logger.info("\n🤝 Demonstrating Dynamic Team Formation...")
        
        # Define a complex task that requires multiple capabilities
        task_requirements = [
            TaskRequirement(capability="user_interface", required=True, priority=5),
            TaskRequirement(capability="task_orchestration", required=True, priority=5),
            TaskRequirement(capability="mcp_integration", required=True, priority=4),
            TaskRequirement(capability="security_monitoring", required=False, priority=2)
        ]
        
        logger.info("Task Requirements:")
        for req in task_requirements:
            req_type = "Required" if req.required else "Optional"
            logger.info(f"  • {req.capability} ({req_type}, Priority: {req.priority})")
        
        # Find agents that can fulfill these requirements
        available_agents = await self.registry.get_available_agents()
        matches = await self.capability_matcher.find_matching_agents(
            task_requirements, available_agents, max_results=5
        )
        
        logger.info(f"\nFound {len(matches)} potential team members:")
        for match in matches:
            logger.info(f"  • {match.agent.name} (Score: {match.score:.2f})")
            logger.info(f"    Matched: {match.matched_capabilities}")
            if match.missing_capabilities:
                logger.info(f"    Missing: {match.missing_capabilities}")
            if match.compatibility_notes:
                logger.info(f"    Notes: {', '.join(match.compatibility_notes)}")
        
        # Demonstrate optimal team selection
        team = self._select_optimal_team(matches, task_requirements)
        logger.info(f"\n🎯 Optimal Team Selected:")
        for agent in team:
            logger.info(f"  • {agent.name} ({agent.agent_id})")
    
    async def demonstrate_load_balancing(self):
        """Demonstrate load balancing and task assignment"""
        logger.info("\n⚖️ Demonstrating Load Balancing...")
        
        # Set up some basic task requirements
        simple_requirements = [
            TaskRequirement(capability="task_orchestration", required=True, priority=3)
        ]
        
        # Demonstrate different load balancing strategies
        strategies = [
            LoadBalancingStrategy.CAPABILITY_AWARE,
            LoadBalancingStrategy.LEAST_LOADED,
            LoadBalancingStrategy.ROUND_ROBIN
        ]
        
        for strategy in strategies:
            assignment = await self.load_balancer.assign_task(
                f"demo-task-{strategy.value}",
                simple_requirements,
                strategy,
                estimated_load=0.3
            )
            
            if assignment:
                logger.info(f"  {strategy.value}: Assigned to {assignment.agent_id}")
            else:
                logger.info(f"  {strategy.value}: No suitable agent found")
        
        # Show load statistics
        stats = self.load_balancer.get_load_statistics()
        if stats:
            logger.info(f"\nLoad Statistics:")
            logger.info(f"  • Total agents with tasks: {stats.get('total_agents', 0)}")
            logger.info(f"  • Total active tasks: {stats.get('total_tasks', 0)}")
            logger.info(f"  • Average load: {stats.get('average_load', 0):.2f}")
    
    async def demonstrate_health_monitoring(self):
        """Demonstrate health monitoring capabilities"""
        logger.info("\n🏥 Demonstrating Health Monitoring...")
        
        # Perform health checks on all agents
        results = await self.health_monitor.check_all_agents()
        
        logger.info(f"Health check completed for {len(results)} agents:")
        for result in results:
            status_emoji = "✅" if result.success else "❌"
            logger.info(f"  {status_emoji} {result.agent_id}: {result.status.value} "
                       f"({result.response_time_ms:.1f}ms)")
        
        # Show health statistics
        stats = self.health_monitor.get_health_statistics()
        if stats:
            logger.info(f"\nHealth Statistics:")
            logger.info(f"  • Success rate: {stats['success_rate']:.1%}")
            logger.info(f"  • Average response time: {stats['average_response_time_ms']:.1f}ms")
            logger.info(f"  • Total checks: {stats['total_checks']}")
    
    def _select_optimal_team(self, matches: List, requirements: List[TaskRequirement]) -> List:
        """Select an optimal team from capability matches"""
        # Simple team selection algorithm
        # In a full implementation, this would be more sophisticated
        
        team = []
        covered_capabilities = set()
        
        # First, ensure all required capabilities are covered
        for req in requirements:
            if req.required and req.capability not in covered_capabilities:
                # Find the best agent for this capability
                best_match = None
                best_score = -1
                
                for match in matches:
                    if (req.capability in match.matched_capabilities and 
                        match.agent not in team and 
                        match.score > best_score):
                        best_match = match
                        best_score = match.score
                
                if best_match:
                    team.append(best_match.agent)
                    covered_capabilities.update(best_match.matched_capabilities)
        
        return team
    
    async def show_registry_statistics(self):
        """Show overall registry statistics"""
        logger.info("\n📊 Registry Statistics:")
        
        stats = self.registry.get_registry_stats()
        logger.info(f"  • Total agents: {stats['total_agents']}")
        logger.info(f"  • Healthy agents: {stats['healthy_agents']}")
        logger.info(f"  • Offline agents: {stats['offline_agents']}")
        logger.info(f"  • Total capabilities: {stats['total_capabilities']}")
        
        # Show load balancer stats if available
        lb_stats = self.load_balancer.get_load_statistics()
        if lb_stats:
            logger.info(f"  • Load balance ratio: {lb_stats.get('load_balance_ratio', 0):.2f}")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.health_monitor:
            await self.health_monitor.stop_monitoring()
        logger.info("✅ Phase 4 demo cleanup completed")


async def main():
    """Main demo function"""
    demo = Phase4Demo()
    
    try:
        await demo.initialize()
        await demo.demonstrate_agent_discovery()
        await demo.demonstrate_dynamic_team_formation()
        await demo.demonstrate_load_balancing()
        await demo.demonstrate_health_monitoring()
        await demo.show_registry_statistics()
        
        logger.info("\n🎉 Phase 4 Agent Registry Demo Completed Successfully!")
        logger.info("The Agent Registry is now ready for integration with existing ATLAS agents.")
        
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        raise
    finally:
        await demo.cleanup()


if __name__ == "__main__":
    asyncio.run(main())