# Risk Education System

## Overview

The Risk Education System provides **non-blocking** risk analysis and educational tools to help users make informed trading decisions. This system **educates** and **surfaces risk**, but **never blocks** trades (except for technical impossibilities).

## Philosophy

- **Educate, don't restrict** - Users own the decision
- **Surface risk information** - Provide clear, actionable insights
- **Never block execution** - Only prevent technically impossible trades
- **User choice** - Always allow execution after showing risk information

## Commands

### `/analyze <ASSET> <SIZE_USD> <LEVERAGE>`

Analyzes risk scenarios for a proposed position without executing any trades.

**Example:**
```
/analyze ETH 1000 20
```

**Output includes:**
- Position requirements (margin needed)
- Liquidation distance estimation
- Risk level assessment (Conservative/Moderate/Aggressive/Extreme)
- Position quality score (0-100)
- Scenario analysis (0.5%, 1%, 2%, 5%, 10% adverse moves)
- Educational warnings (if applicable)

### `/calc <ASSET> <LEVERAGE> [risk_pct]`

Calculates suggested position sizes based on risk tolerance.

**Examples:**
```
/calc ETH 20          # Show all risk tiers
/calc ETH 20 5        # Show size for 5% risk
```

**Output includes:**
- Conservative (2% risk), Moderate (5% risk), Aggressive (10% risk) suggestions
- Position quality assessment for calculated sizes
- Margin requirements

## Risk Assessment Components

### Risk Levels
- **🟢 Conservative** - Low account risk (< 2%)
- **🟡 Moderate** - Moderate account risk (2-5%)
- **🟠 Aggressive** - High account risk (5-10%)
- **🔴 Extreme** - Very high account risk (> 10%)

### Leverage Categories
- **Conservative** - < 10x
- **Moderate** - 10-49x
- **High** - 50-99x
- **Very High** - 100-199x
- **Ultra-High** - 200x+

### Position Quality Score
- **Excellent (80-100)** - Conservative risk profile with good safety margins
- **Good (60-79)** - Moderate risk with reasonable safety margins
- **Risky (40-59)** - High risk—monitor closely
- **Very Risky (0-39)** - Extreme risk—minimal safety margin

### Educational Warnings
- **Protocol Capability** - Information about Avantis protocol limits
- **High/Ultra-High Leverage** - Warnings about leverage amplification
- **Account Risk** - Warnings about high account risk scenarios
- **Liquidation Distance** - Warnings when close to liquidation

## Configuration

Risk education can be configured via environment variables:

```bash
# Risk education (non-blocking)
RISK_EDUCATION_ENABLED=true
RISK_WARN_LEVERAGE_HIGH=50
RISK_WARN_LEVERAGE_EXTREME=200
RISK_WARN_LIQUIDATION_PCT=0.01
RISK_SCENARIO_STRESS_MOVE=0.02
RISK_PROTOCOL_MAX_LEVERAGE=500
```

## Technical Implementation

### Risk Calculator Service
- **Location**: `src/services/risk_calculator.py`
- **Purpose**: Pure educational analysis (no blocking)
- **Dependencies**: None (self-contained)

### Handler Integration
- **Location**: `src/bot/handlers/risk_edu_handlers.py`
- **Integration**: Added to handler registry
- **Middleware**: Uses existing user middleware for authentication

### Settings Integration
- **Location**: `src/config/settings.py`
- **Environment**: `env.example` updated with risk education settings
- **Toggles**: Can be enabled/disabled without code changes

## Hard Limits (Technical Only)

The system only blocks trades for:

1. **Insufficient Balance** - Not enough margin for the position
2. **Invalid Inputs** - Negative values, zero leverage, etc.
3. **Technical Errors** - System failures, stale price data

## Integration with Existing Trading Flow

- **Additive approach** - New commands complement existing `/trade` flow
- **No disruption** - Existing trading functionality remains unchanged
- **Optional confirmation** - Can be extended to show risk analysis before execution (future enhancement)

## Usage Examples

### Conservative Position Analysis
```
/analyze BTC 500 5
```
Shows conservative 5x leverage position with low risk scenarios.

### High-Risk Position Analysis
```
/analyze SOL 5000 100
```
Shows high-leverage position with detailed risk warnings and scenarios.

### Position Sizing Calculator
```
/calc ETH 20 3
```
Calculates position size for 3% account risk at 20x leverage.

## Testing

Run the test suite:
```bash
pytest tests/test_risk_calculator.py -v
```

Tests cover:
- Basic risk analysis functionality
- High leverage scenarios
- Error handling for invalid inputs
- Warning generation logic
- Position quality scoring

## Future Enhancements

1. **Confirmation Overlay** - Optional risk analysis before trade execution
2. **Historical Analysis** - Backtesting scenarios against historical data
3. **Portfolio Risk** - Multi-position risk assessment
4. **Custom Scenarios** - User-defined stress test scenarios
5. **Risk Limits** - Optional user-set risk limits (still non-blocking)

## Support

For questions about the risk education system:
- Check the help command: `/help`
- Review this documentation
- Contact support for technical issues

Remember: **This system educates but never restricts. Your money, your choice.**
