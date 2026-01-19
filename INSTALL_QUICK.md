# 🚀 Installation Rapide AR_AS

> **Si Docker échoue avec des erreurs DNS**, suivez ces étapes:

## ⚡ Solution Automatique (Recommandé)

### Une seule commande pour tout réparer:

```bash
cd ~/Documents/Music/AR_AS
bash scripts/fix-docker-dns.sh
```

Ce script va:
1. ✅ Configurer les DNS Docker (Google DNS + Cloudflare)
2. ✅ Redémarrer Docker automatiquement
3. ✅ Vérifier que tout fonctionne
4. ✅ Vous dire quoi faire ensuite

---

## 📦 Après avoir exécuté le script

```bash
# Option 1: Build complet
make build
make up

# Option 2: Mode développement (avec hot-reload)
make dev
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
