#!/bin/bash
# ==============================================================================
# Installation Locale de PyTorch CPU
# ==============================================================================
# Ce script installe PyTorch version CPU (léger, ~250 MB) au lieu de la version
# avec CUDA (~2.5 GB). Utile pour développement local sans GPU.
#
# Usage: ./scripts/install-torch-cpu.sh
# ==============================================================================

set -e

echo "=================================================="
echo "Installation PyTorch CPU-only (version légère)"
echo "=================================================="
echo ""

# Couleurs pour output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Version:${NC} torch==2.9.1+cpu (~250 MB)"
echo -e "${YELLOW}Index:${NC} https://download.pytorch.org/whl/cpu"
echo ""

# Vérifier si torch est déjà installé
if python -c "import torch" 2>/dev/null; then
    CURRENT_VERSION=$(python -c "import torch; print(torch.__version__)")
    echo -e "${YELLOW}Torch actuel:${NC} $CURRENT_VERSION"

    if [[ $CURRENT_VERSION == *"+cpu"* ]]; then
        echo -e "${GREEN}✓${NC} Version CPU déjà installée !"
        exit 0
    else
        echo -e "${YELLOW}⚠${NC}  Version CUDA détectée, désinstallation..."
        pip uninstall -y torch
    fi
fi

echo ""
echo "Installation de PyTorch CPU-only..."
pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu

echo ""
echo -e "${GREEN}✓ Installation terminée !${NC}"
echo ""

# Vérifier l'installation
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"

echo ""
echo "=================================================="
echo "Prochaines étapes:"
echo "  pip install -r requirements.txt"
echo "=================================================="
