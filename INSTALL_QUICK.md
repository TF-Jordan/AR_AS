# 🚀 Installation Rapide AR_AS

> **Si Docker échoue avec des erreurs DNS**, suivez ces étapes:

## ⚡ Solution Ultime - Build avec Réseau Host

### Si le DNS ne fonctionne toujours pas, utilisez cette commande magique:

```bash
cd ~/Documents/Music/AR_AS

# Cette commande contourne TOUS les problèmes DNS
bash scripts/build-with-host-network.sh

# Puis démarrer les services
docker-compose up -d
```

**Pourquoi ça marche?** Le build utilise le réseau de votre machine directement (--network=host), donc il utilise votre connexion internet qui fonctionne!

---

## 🎯 Méthode Alternative avec docker-compose

```bash
cd ~/Documents/Music/AR_AS

# Build avec fix DNS intégré
docker-compose -f docker-compose.yml -f docker-compose.build-fix.yml build

# Démarrer
docker-compose up -d
```

---

## 📦 Après le build réussi

```bash
# Vérifier que tout tourne
docker-compose ps

# Voir les logs
docker-compose logs -f api

# Accéder à l'API
curl http://localhost:8000/docs
```

---

## 🐛 Si vous avez toujours des problèmes

### Problème: "Temporary failure resolving 'deb.debian.org'"

**Solution manuelle:**

```bash
# 1. Configurer daemon.json
sudo tee /var/snap/docker/3377/config/daemon.json > /dev/null <<'EOF'
{
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
EOF

# 2. Redémarrer Docker
sudo snap restart docker

# 3. Attendre 20 secondes
sleep 20

# 4. Tester DNS
docker run --rm alpine nslookup google.com

# 5. Si ça marche, lancer le build
cd ~/Documents/Music/AR_AS
make build
```

---

## 📖 Documentation Complète

Pour la documentation complète, voir:
- **README.md** - Documentation complète du projet
- **docs/DOCKER.md** - Guide Docker détaillé
- **docs/ARCHITECTURE.md** - Architecture système

---

## 🆘 Support

Si rien ne fonctionne:

1. Vérifiez votre connexion internet: `ping 8.8.8.8`
2. Vérifiez Docker: `docker ps`
3. Vérifiez les logs Docker: `sudo journalctl -u snap.docker.dockerd -n 50`
