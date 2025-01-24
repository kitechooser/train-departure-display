# Train Departure Display Migration Plan

## Overview
This document outlines the step-by-step plan to migrate the Train Departure Display application to a new event-driven architecture while maintaining functionality throughout the process.

## Phase 1: API and Domain Layer
**Goal**: Separate API concerns and introduce domain models while maintaining existing functionality.

### Steps:

1. Create API Layer Structure
```bash
mkdir -p src/api
mkdir -p src/domain/models
mkdir -p src/domain/processors
```

2. Create Base API Client
- Create `src/api/base_client.py`
- Implement common HTTP functionality
- Add error handling and retry logic
- Add logging

3. Implement TfL API Client
- Create `src/api/tfl_client.py`
- Move TfL API logic from `src/tfl.py`
- Add new error handling
- Support both old and new implementations via config flag

4. Implement Rail API Client
- Create `src/api/rail_client.py`
- Move rail API logic from `src/trains.py`
- Add new error handling
- Support both old and new implementations via config flag

5. Create Domain Models
- Create `src/domain/models/station.py`
- Create `src/domain/models/service.py`
- Create `src/domain/models/status.py`
- Implement conversion from both TfL and Rail responses

6. Create Data Processors
- Create `src/domain/processors/departure_processor.py`
- Create `src/domain/processors/status_processor.py`
- Add unified processing logic

### Testing Requirements:
1. Unit Tests
- Test each new API client
- Test domain model conversions
- Test processors
- Verify error handling

2. Integration Tests
- Test API clients with live endpoints
- Verify data conversion accuracy
- Compare old vs new implementation results

3. Manual Testing
- Run application with new implementation flag off
- Run application with new implementation flag on
- Compare display outputs
- Verify no performance degradation

### Rollback Procedure:
1. Disable new implementation flag in config
2. Remove new directories if needed
3. Revert any modified files to original state

## Phase 2: Infrastructure Layer
**Goal**: Implement event system and queues while maintaining existing refresh logic.

### Steps:

1. Create Infrastructure Layer
```bash
mkdir -p src/infrastructure
```

2. Implement Event Bus
- Create `src/infrastructure/event_bus.py`
- Implement publish/subscribe mechanism
- Add event logging
- Support both sync and async events

3. Implement Queue Manager
- Create `src/infrastructure/queue_manager.py`
- Add departure queue
- Add announcement queue
- Add status queue

4. Add Configuration Manager
- Create `src/infrastructure/config_manager.py`
- Support feature flags
- Add migration settings

5. Integrate with Existing Code
- Add event emission to API clients
- Add queue processing to main loop
- Maintain existing refresh mechanism

### Testing Requirements:
1. Unit Tests
- Test event bus functionality
- Test queue operations
- Verify event handling

2. Integration Tests
- Test event flow through system
- Verify queue processing
- Check performance impact

3. Manual Testing
- Monitor event logs
- Verify display updates
- Check announcement timing

### Rollback Procedure:
1. Disable event system in config
2. Revert to direct API calls
3. Remove event listeners

## Phase 3: Display Components
**Goal**: Refactor display logic into reusable components while maintaining existing display functionality.

### Steps:

1. Create Component Structure
```bash
mkdir -p src/presentation/displays
mkdir -p src/presentation/renderers/components
mkdir -p src/presentation/renderers/layouts
```

2. Create Base Components
- Create `src/presentation/renderers/components/text.py`
- Create `src/presentation/renderers/components/scroll.py`
- Create `src/presentation/renderers/components/status.py`

3. Create Layout Managers
- Create `src/presentation/renderers/layouts/grid.py`
- Create `src/presentation/renderers/layouts/row.py`
- Implement pixel position calculations

4. Create Display Classes
- Create `src/presentation/displays/base_display.py`
- Create `src/presentation/displays/tfl_display.py`
- Create `src/presentation/displays/rail_display.py`

5. Integrate with Event System
- Add event listeners to displays
- Connect components to event bus
- Maintain existing refresh mechanism

### Testing Requirements:
1. Unit Tests
- Test each component
- Test layout calculations
- Verify event handling

2. Integration Tests
- Test component interactions
- Verify layout rendering
- Check display updates

3. Manual Testing
- Compare display output
- Verify animations
- Check performance

### Rollback Procedure:
1. Disable new display system
2. Revert to original renderers
3. Remove new component listeners

## Phase 4: Full Integration
**Goal**: Complete migration to new architecture while ensuring system stability.

### Steps:

1. Create Service Layer
```bash
mkdir -p src/services
```

2. Implement Services
- Create `src/services/announcement_service.py`
- Create `src/services/display_service.py`
- Create `src/services/status_service.py`

3. Connect All Components
- Wire up event bus to all services
- Connect queues to processors
- Integrate display components

4. Clean Up Old Code
- Remove duplicate functionality
- Clean up old implementations
- Update configuration

5. Final Integration
- Update main application loop
- Optimize event flow
- Add performance monitoring

### Testing Requirements:
1. Unit Tests
- Test all services
- Verify event chains
- Check error handling

2. Integration Tests
- Test full system flow
- Verify all features
- Check migration completeness

3. Manual Testing
- Full system testing
- Performance benchmarking
- User experience verification

### Rollback Procedure:
1. Revert to previous phase
2. Restore old main loop
3. Remove service layer

## Configuration Changes
Each phase requires specific configuration changes to support gradual migration:

```json
{
  "migration": {
    "phase1_enabled": false,
    "phase2_enabled": false,
    "phase3_enabled": false,
    "phase4_enabled": false,
    "use_new_api_client": false,
    "use_event_system": false,
    "use_new_display": false
  }
}
```

## Monitoring and Logging
Each phase should include:
- Enhanced logging for new components
- Performance metrics collection
- Error tracking
- Feature flag status

## Success Criteria
Each phase must meet these criteria before proceeding:
1. All tests passing
2. No performance degradation
3. All features working as before
4. No user-visible regressions
5. Clean error logs
6. Successful rollback test

## Commands for Testing Each Phase

### Phase 1 Testing
```bash
# Run unit tests
python -m pytest tests/api tests/domain

# Test with new API client
python src/main.py --use-new-api

# Compare outputs
python tools/compare_outputs.py
```

### Phase 2 Testing
```bash
# Run event system tests
python -m pytest tests/infrastructure

# Monitor event flow
python src/main.py --debug-events

# Test queue processing
python tools/test_queues.py
```

### Phase 3 Testing
```bash
# Test display components
python -m pytest tests/presentation

# Visual regression testing
python tools/compare_displays.py

# Performance testing
python tools/benchmark_display.py
```

### Phase 4 Testing
```bash
# Full system tests
python -m pytest tests/

# Integration testing
python tools/integration_test.py

# Load testing
python tools/load_test.py
```

## Notes
- Each phase can be implemented and tested independently
- Feature flags allow gradual rollout
- Maintain backwards compatibility until final phase
- Each phase has specific success criteria
- Full testing required before moving to next phase
