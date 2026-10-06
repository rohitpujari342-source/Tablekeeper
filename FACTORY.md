#TableOps Factory
##Overview
TableOps is a multi-agent software engineering factory designed to plan, implement, verify, and improve software through coordinated coding agents.

The factory was used to build and evolve **Tablekeeper**, a restaurant reservation service for the Dark Factory challenge.

The factory follows a simple operating loop:

**Plan → Implement → Verify → Correct → Ship**

The key design principle is separation of responsibilities. The agent that plans the work is different from the agent that implements it, and implementation is independently verified before being considered complete.

