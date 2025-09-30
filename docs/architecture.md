# Vanta Bot Architecture

## Overview

Vanta Bot is a production-ready Telegram trading bot for the Avantis Protocol on Base network. It features a layered architecture designed for scalability, maintainability, and security.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Vanta Bot System                          │
├─────────────────────────────────────────────────────────────┤
│  Telegram Bot Layer                                         │
│  ├── Handlers (Commands, Callbacks, Messages)              │
│  ├── Middleware (Auth, Rate Limiting, Error Handling)      │
│  └── Keyboards (Dynamic UI Components)                     │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer                                       │
│  ├── Trading Services (Order Management, Execution)       │
│  ├── Portfolio Services (Position Tracking, Analytics)   │
│  ├── Copy Trading Services (Leader Following)             │
│  └── Risk Management (Position Limits, Slippage Control)   │
├─────────────────────────────────────────────────────────────┤
│  Blockchain Integration Layer                               │
│  ├── Avantis SDK Integration                               │
│  ├── Web3 Client (Transaction Building, Signing)           │
│  ├── Price Feed Services (Chainlink, Pyth)                │
│  └── Wallet Management (Key Storage, Signing)              │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ├── PostgreSQL (User Data, Positions, Transactions)      │
│  ├── Redis (Caching, Session Management)                   │
│  └── File Storage (Logs, Backups)                          │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                       │
│  ├── Docker Containers                                     │
│  ├── Health Monitoring                                     │
│  ├── Metrics Collection                                    │
│  └── Logging & Tracing                                     │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Telegram Bot Layer (`src/bot/`)

**Handlers** (`src/bot/handlers/`)
- Command handlers for user interactions
- Callback handlers for inline keyboards
- Message handlers for natural language processing
- Admin handlers for system management

**Middleware** (`src/bot/middleware/`)
- Authentication and authorization
- Rate limiting and DDoS protection
- Error handling and logging
- User session management

**Keyboards** (`src/bot/keyboards/`)
- Dynamic inline keyboards
- Trading interface components
- Navigation and menu systems

### 2. Business Logic Layer (`src/services/`)

**Trading Services** (`src/services/trading/`)
- Order execution and management
- Position tracking and monitoring
- Trade validation and risk checks
- Slippage and fee calculations

**Portfolio Services** (`src/services/portfolio/`)
- Portfolio analytics and reporting
- Performance tracking
- Risk metrics calculation
- Position sizing algorithms

**Copy Trading Services** (`src/services/copy_trading/`)
- Leader identification and following
- Position mirroring
- Risk-adjusted position sizing
- Performance attribution

### 3. Blockchain Integration (`src/blockchain/`)

**Avantis SDK Integration**
- Protocol-specific trading functions
- Market data and price feeds
- Position and account management
- Risk parameter configuration

**Web3 Client**
- Transaction building and signing
- Gas estimation and optimization
- Nonce management
- Transaction monitoring

**Price Feed Services**
- Chainlink price feeds (primary)
- Pyth Network feeds (fallback)
- Price validation and staleness checks
- Multi-source price aggregation

### 4. Data Layer (`src/database/`)

**Models** (`src/database/models.py`)
- SQLAlchemy ORM models
- User accounts and preferences
- Trading positions and transactions
- System configuration and settings

**Repositories** (`src/database/repositories/`)
- Data access layer abstraction
- Query optimization
- Transaction management
- Caching strategies

### 5. Configuration Management (`src/config/`)

**Settings** (`src/config/settings.py`)
- Environment-based configuration
- Pydantic validation
- Secret management
- Feature flags

**Validation** (`src/config/validate.py`)
- Configuration validation
- Dependency checks
- Security audits
- Runtime verification

## Data Flow

### Trading Flow
1. User sends trading command via Telegram
2. Handler validates user permissions and rate limits
3. Trading service validates trade parameters
4. Risk service checks position limits and exposure
5. Blockchain service builds and signs transaction
6. Transaction is submitted to network
7. Position is updated in database
8. User receives confirmation and updates

### Copy Trading Flow
1. Leader opens position (detected via monitoring)
2. Copy trading service evaluates leader performance
3. Risk-adjusted position size is calculated
4. Position is mirrored for followers
5. Performance is tracked and reported
6. Risk limits are enforced per follower

### Price Feed Flow
1. Multiple price sources are monitored
2. Prices are validated for staleness and accuracy
3. Primary source (Chainlink) is preferred
4. Fallback sources (Pyth) are used if needed
5. Prices are cached in Redis for performance
6. Stale or invalid prices trigger alerts

## Security Architecture

### Key Management
- Private keys encrypted with AES-256
- KMS integration for production environments
- Hardware security module (HSM) support
- Key rotation and backup strategies

### Authentication & Authorization
- Telegram user authentication
- Role-based access control (RBAC)
- Admin privilege escalation
- Session management and timeout

### Data Protection
- Database encryption at rest
- Secure communication (TLS/SSL)
- Input validation and sanitization
- SQL injection prevention

### Risk Management
- Position size limits
- Leverage restrictions
- Slippage tolerance controls
- Circuit breakers for extreme conditions

## Monitoring & Observability

### Health Monitoring
- Application health endpoints
- Database connectivity checks
- Blockchain network status
- External API availability

### Metrics Collection
- Trading volume and frequency
- User activity and engagement
- System performance metrics
- Error rates and response times

### Logging & Tracing
- Structured logging with correlation IDs
- Request/response tracing
- Error tracking and alerting
- Audit trails for compliance

## Deployment Architecture

### Container Strategy
- Multi-stage Docker builds
- Production and development images
- Security scanning and validation
- Resource limits and constraints

### Orchestration
- Docker Compose for development
- Kubernetes for production
- Service discovery and load balancing
- Auto-scaling and failover

### CI/CD Pipeline
- Automated testing and validation
- Security scanning and compliance
- Multi-environment deployments
- Rollback and recovery procedures

## Scalability Considerations

### Horizontal Scaling
- Stateless service design
- Database connection pooling
- Redis clustering for caching
- Load balancing strategies

### Performance Optimization
- Database query optimization
- Caching strategies
- Async/await patterns
- Resource pooling and reuse

### Fault Tolerance
- Circuit breaker patterns
- Retry mechanisms with backoff
- Graceful degradation
- Disaster recovery procedures

## Development Guidelines

### Code Organization
- Modular, single-responsibility components
- Dependency injection for testability
- Interface-based design
- Comprehensive error handling

### Testing Strategy
- Unit tests for business logic
- Integration tests for external dependencies
- End-to-end tests for critical paths
- Performance and load testing

### Documentation
- API documentation with examples
- Architecture decision records (ADRs)
- Deployment and operations guides
- Troubleshooting and FAQ sections