#!/bin/bash
# Run tests script

set -e

echo "================================"
echo "API Optimizer - Test Suite"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Run unit tests
echo -e "${YELLOW}Running unit tests...${NC}"
pytest tests/unit/ -v --tb=short || exit 1
echo -e "${GREEN}✅ Unit tests passed${NC}"
echo ""

# Run integration tests
echo -e "${YELLOW}Running integration tests...${NC}"
pytest tests/integration/ -v --tb=short || exit 1
echo -e "${GREEN}✅ Integration tests passed${NC}"
echo ""

# Run all tests with coverage
echo -e "${YELLOW}Running all tests with coverage...${NC}"
pytest tests/ -v --cov=app --cov-report=html --cov-report=term || exit 1
echo -e "${GREEN}✅ Coverage report generated${NC}"
echo ""

echo -e "${GREEN}================================"
echo "All tests passed! ✅"
echo "================================${NC}"
