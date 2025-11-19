#!/usr/bin/env bash
# Setup script for development environment
# Installs git hooks and dependencies

set -e

echo "🚀 Setting up Claire de Binaire development environment..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Install Python dependencies
echo -e "\n${YELLOW}📦 Installing Python dependencies...${NC}"
pip install -q -r requirements-dev.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"

# 2. Install pre-commit hook
echo -e "\n${YELLOW}🪝 Installing git hooks...${NC}"
if [ -f ".git/hooks/pre-commit" ]; then
    echo -e "${GREEN}✅ Pre-commit hook already installed${NC}"
else
    cp scripts/hooks/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo -e "${GREEN}✅ Pre-commit hook installed${NC}"
fi

# 3. Verify setup
echo -e "\n${YELLOW}🔍 Verifying setup...${NC}"
python -m pytest --version
python -m pytest --co -q | head -5
echo -e "${GREEN}✅ Setup complete!${NC}"

echo -e "\n${GREEN}🎉 Development environment ready!${NC}"
echo -e "\nRun tests with: ${YELLOW}pytest -v${NC}"
echo -e "Run with coverage: ${YELLOW}pytest --cov=services${NC}"
