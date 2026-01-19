#!/bin/bash
# ==============================================================================
# Script pour configurer les DNS Docker et résoudre les problèmes de build
# ==============================================================================

set -e  # Exit on error

echo "🔧 Configuration des DNS Docker..."
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les erreurs
error() {
    echo -e "${RED}❌ ERREUR: $1${NC}"
    exit 1
}

# Fonction pour afficher les succès
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Fonction pour afficher les infos
info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Fonction pour afficher les warnings
warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Vérifier si on est sur Ubuntu/Debian avec snap Docker
if ! command -v snap &> /dev/null; then
    error "Snap n'est pas installé. Ce script est conçu pour Docker installé via snap."
fi

# Vérifier que Docker est installé
if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé."
fi

info "Docker détecté: $(docker --version)"

# Chemin de la configuration Docker (snap)
DOCKER_CONFIG="/var/snap/docker/current/config/daemon.json"

# Vérifier si le répertoire existe
CONFIG_DIR=$(dirname "$DOCKER_CONFIG")
if [ ! -d "$CONFIG_DIR" ]; then
    warning "Répertoire de configuration Docker non trouvé: $CONFIG_DIR"
    info "Recherche d'autres emplacements..."

    # Chercher le bon emplacement
    if [ -d "/var/snap/docker/3377/config" ]; then
        DOCKER_CONFIG="/var/snap/docker/3377/config/daemon.json"
        success "Trouvé: /var/snap/docker/3377/config"
    elif [ -d "/etc/docker" ]; then
        DOCKER_CONFIG="/etc/docker/daemon.json"
        success "Trouvé: /etc/docker"
    else
        error "Impossible de trouver le répertoire de configuration Docker"
    fi
fi

CONFIG_DIR=$(dirname "$DOCKER_CONFIG")
info "Configuration sera créée dans: $DOCKER_CONFIG"

# Backup de la configuration existante
if [ -f "$DOCKER_CONFIG" ]; then
    warning "Configuration existante détectée"
    sudo cp "$DOCKER_CONFIG" "${DOCKER_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
    success "Backup créé: ${DOCKER_CONFIG}.backup.*"
fi

# Créer la nouvelle configuration avec DNS
info "Création de la configuration DNS..."
sudo tee "$DOCKER_CONFIG" > /dev/null <<'EOF'
{
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"],
  "dns-opts": ["ndots:0"],
  "log-level": "info"
}
EOF

success "Configuration DNS créée"

# Afficher la configuration
info "Configuration actuelle:"
sudo cat "$DOCKER_CONFIG"
echo ""

# Redémarrer Docker
info "Redémarrage de Docker..."
sudo snap restart docker || error "Impossible de redémarrer Docker"

# Attendre que Docker démarre
info "Attente du démarrage de Docker (20 secondes)..."
sleep 20

# Vérifier que Docker fonctionne
info "Vérification de Docker..."
if ! docker ps &> /dev/null; then
    error "Docker ne répond pas après le redémarrage"
fi
success "Docker fonctionne"

# Tester la résolution DNS
info "Test de résolution DNS dans un conteneur..."
if docker run --rm alpine nslookup deb.debian.org &> /dev/null; then
    success "DNS fonctionne! deb.debian.org est accessible"
else
    error "DNS ne fonctionne toujours pas. Vérifiez votre connexion internet."
fi

# Test Google DNS
info "Test avec google.com..."
if docker run --rm alpine nslookup google.com &> /dev/null; then
    success "google.com est accessible"
else
    warning "google.com n'est pas accessible"
fi

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Configuration DNS Docker terminée avec succès!        ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
info "Vous pouvez maintenant lancer le build:"
echo -e "  ${BLUE}cd ~/Documents/Music/AR_AS${NC}"
echo -e "  ${BLUE}make build${NC}"
echo -e "  ${BLUE}# OU${NC}"
echo -e "  ${BLUE}make dev${NC}"
echo ""
