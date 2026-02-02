# OpyTown

🏆 **SanD Hackathon 2026 Award Winner**

## About This Project

### AGNTCY Track — Multi-Agent Systems Challenge

OpyTown was developed as part of the **🤖 AGNTCY Track — Multi-Agent Systems Challenge**, which introduces participants to multi-agent systems (MAS) using [AGNTCY](https://github.com/agntcy), an open-source project initiated at **Cisco** that is building foundational infrastructure for the **Internet of Agents**.

The challenge provides teams with the opportunity to explore and build upon AGNTCY's core components, including:

- **Agent-to-Agent (A2A) communication protocols** for seamless inter-agent messaging
- **Multi-agent orchestration** using directed graphs and LangGraph
- **Interoperable transport layers** (SLIM, NATS, and other protocols)
- **Observability and metrics** through OpenTelemetry integration
- **Model Context Protocol (MCP)** for external service integration

Teams can start at any challenge level based on their experience, from basic agent communication to advanced multi-agent coordination and custom protocol implementations.

### Hackathon Award

🏆 **This project was awarded at the SanD Hackathon 2026**, recognizing its innovative approach to building a production-ready multi-agent system with comprehensive observability, flexible deployment options, and real-world applicability.

## What is OpyTown?

OpyTown is an **interactive multi-agent system** that combines the power of AGNTCY's infrastructure with an engaging game-based visualization interface. It demonstrates how autonomous agents can communicate, coordinate, and collaborate in real-time within a virtual town environment.

### Key Features

#### 🎮 Interactive Game-Based UI
- Real-time visualization of agent interactions in a virtual town
- Live agent movement and communication display
- Interactive chat interface for engaging with agents
- Visual representation of multi-agent coordination

#### 🤖 Advanced Multi-Agent System
- **Supervisor-Worker Architecture**: Hierarchical agent coordination with supervisor agents managing worker agents
- **Agent-to-Agent Communication**: Direct A2A messaging using AGNTCY protocols
- **Publish/Subscribe Patterns**: Efficient broadcast and unicast messaging
- **LangGraph Integration**: Directed graph-based agent workflows for complex decision-making

#### 🔧 Production-Ready Infrastructure
- **Kubernetes Deployment**: Full Helm charts for production-grade orchestration
- **Docker Compose**: Quick local development setup
- **Multiple Deployment Options**: Local Python, Docker, or Kubernetes
- **Flexible LLM Provider Support**: Integration with OpenAI, Azure, GROQ, NVIDIA NIM, and custom providers via LiteLLM

#### 📊 Comprehensive Observability
- **Advanced Observability Stack**: Grafana, ClickHouse, and OpenTelemetry integration
- **Metrics Computation Engine (MCE)**: Evaluate multi-agent system performance with metrics like:
  - Agent-to-Agent interactions
  - Tool utilization accuracy
  - Workflow efficiency
  - Goal success rate
  - Context preservation
- **Real-time Trace Visualization**: Monitor agent behavior and system performance
- **Custom Dashboards**: Pre-configured Grafana dashboards for system insights

#### 🌐 External Service Integration
- **MCP Server Integration**: Real-time external data integration (weather API)
- **Extensible Architecture**: Easy addition of new agents and services
- **Configurable Transport Layers**: Support for multiple messaging protocols

## New Implementations

This project extends the original AGNTCY framework with several innovative features:

1. **Game-Based Visualization**: An immersive UI that makes multi-agent interactions tangible and engaging
2. **Hybrid Interaction Model**: Combines movement-based interaction with traditional messaging
3. **Real-Time Agent Coordination**: Live updates showing agent decision-making and collaboration
4. **Production Deployment**: Complete Kubernetes infrastructure with Helm charts
5. **Comprehensive Metrics**: Advanced evaluation framework for multi-agent system performance
6. **Flexible Architecture**: Modular design allowing easy extension and customization

## Getting Started

For detailed setup instructions, deployment options, and usage guides, please refer to the [OpyTown README](./OpyTown/README.md).

### Quick Start

```bash
# Clone the repository
cd OpyTown

# Run with Docker Compose (recommended)
docker compose up

# Access the UI at http://localhost:3000
# Access Grafana at http://localhost:3001
```

## Project Structure

- **`OpyTown/`**: Main project directory containing the multi-agent system implementation
  - **`agents/`**: Agent implementations (supervisors, farms, MCP servers)
  - **`frontend/`**: Interactive game-based UI
  - **`deployment/`**: Kubernetes Helm charts and deployment configurations
  - **`docs/`**: Additional documentation

## Technologies Used

- **AGNTCY**: Core multi-agent infrastructure
- **LangGraph**: Agent workflow orchestration
- **OpenTelemetry**: Distributed tracing and observability
- **Grafana & ClickHouse**: Metrics visualization and storage
- **Docker & Kubernetes**: Containerization and orchestration
- **React**: Frontend UI framework
- **FastAPI**: Backend API framework
- **LiteLLM**: Multi-provider LLM integration

## Acknowledgments

- **AGNTCY Team** at Cisco for creating the foundational infrastructure
- **SanD Hackathon 2026** organizers and judges
- The open-source community for the amazing tools and frameworks

## License

This project builds upon the AGNTCY open-source framework. Please refer to individual component licenses for details.
