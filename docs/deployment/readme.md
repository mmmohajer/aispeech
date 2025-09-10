# Application Deployment Guide

This document provides a comprehensive, step-by-step guide for deploying and hardening your server for the application. Follow each section carefully to ensure a secure and reliable deployment.

---

# Table of Contents

- [1. Initial Server Hardening](#1-initial-server-hardening)
  - [1.1. Login and User Setup](#11-login-and-user-setup)
  - [1.2. Disable Root Login via SSH](#12-disable-root-login-via-ssh)
- [2. SSH Key Authentication](#2-ssh-key-authentication)
  - [2.1. Generate SSH Keys (Local Machine)](#21-generate-ssh-keys-local-machine)
  - [2.2. Copy Public Key to Server](#22-copy-public-key-to-server)
  - [2.3. Configure Server for Key Authentication](#23-configure-server-for-key-authentication)
  - [2.4. Test SSH Key Login](#24-test-ssh-key-login)
- [3. SSH Config Alias (Local Machine)](#3-ssh-config-alias-local-machine)
- [4. System Updates & Firewall](#4-system-updates--firewall)
  - [4.1. Update & Upgrade](#41-update--upgrade)
  - [4.2. Configure UFW Firewall](#42-configure-ufw-firewall)
- [5. Install & Configure fail2ban](#5-install--configure-fail2ban)
- [6. Install Docker & Docker Compose](#6-install-docker--docker-compose)
- [7. Git Configuration & SSH for GitHub](#7-git-configuration--ssh-for-github)
- [8. Clone the Repository](#8-clone-the-repository)
- [9. Application Setup](#9-application-setup)
  - [9.1. Create Required Folders](#91-create-required-folders)
  - [9.2. Update Configuration Files](#92-update-configuration-files)
  - [9.3. Set Executable Permissions](#93-set-executable-permissions)
  - [9.4. Setup HTTP Basic Auth for Flower (Optional)](#94-setup-http-basic-auth-for-flower-optional)
  - [9.5. SSL Certificate Setup](#95-ssl-certificate-setup)
  - [9.6. Clean Up Docker (Optional)](#96-clean-up-docker-optional)
  - [9.7. Test SSL Setup](#97-test-ssl-setup)
  - [9.8. Production Deployment](#98-production-deployment)
- [10. Docker Swarm & GlusterFS Deployment](#10-docker-swarm--glusterfs-deployment)
  - [10.1. Swarm Architecture Overview](#101-swarm-architecture-overview)
  - [10.2. Swarm Cluster Setup](#102-swarm-cluster-setup)
    - [10.2.1. Initialize Swarm on Manager](#1021-initialize-swarm-on-manager)
    - [10.2.2. Join Worker Nodes](#1022-join-worker-nodes)
    - [10.2.3. Join Additional Manager Nodes (Optional)](#1023-join-additional-manager-nodes-optional)
    - [10.2.4. Verify Cluster](#1024-verify-cluster)
  - [10.3. GlusterFS Setup](#103-glusterfs-setup)
    - [10.3.1. Install GlusterFS on All Nodes](#1031-install-glusterfs-on-all-nodes)
  - [10.4. Onboarding a New Node to GlusterFS Cluster](#104-onboarding-a-new-node-to-glusterfs-cluster)
    - [1. Prepare the New Node](#1-prepare-the-new-node)
    - [2. Add the New Node to the Cluster (from any existing node)](#2-add-the-new-node-to-the-cluster-from-any-existing-node)
    - [3. (If needed) Update the Volume to Include the New Node](#3-if-needed-update-the-volume-to-include-the-new-node)
    - [4. Mount the GlusterFS Volume on the New Node](#4-mount-the-glusterfs-volume-on-the-new-node)
      - [(Optional) Auto-mount on Boot](#optional-auto-mount-on-boot)
      - [(Optional) Systemd Service for Mounting](#optional-systemd-service-for-mounting)
  - [10.5. GlusterFS Watchdog Service](#105-glusterfs-watchdog-service)
  - [10.6. Useful Docker Swarm Commands](#106-useful-docker-swarm-commands)
- [11. Continuous Integration & Continuous Deployment (CI/CD)](#11-continuous-integration--continuous-deployment-cicd)

## 1. Initial Server Hardening

### 1.1. Login and User Setup

1. **Login to the server as root:**
   ```sh
   ssh root@IP_ADDRESS
   ```
2. **Change the root user password:**
   ```sh
   passwd
   ```
3. **Add a new user:**
   ```sh
   adduser USER_NAME
   ```
4. **Grant sudo privileges to the new user:**
   - Open the sudoers file:
     ```sh
     visudo
     ```
   - Add the following line under root privileges:
     ```
     USER_NAME ALL=(ALL:ALL) ALL
     ```

### 1.2. Disable Root Login via SSH

1. Navigate to the SSH config directory:
   ```sh
   cd /etc/ssh/
   cp sshd_config sshd_config.bak
   nano sshd_config
   ```
2. Change the following line:
   ```
   PermitRootLogin no
   ```
3. Save and exit (`Ctrl+X`), then restart SSH:
   ```sh
   systemctl restart ssh
   ```
4. **Login as the new user:**
   ```sh
   ssh USER_NAME@IP_ADDRESS
   ```
5. **Switch to root (if needed):**
   ```sh
   sudo -s
   ```

---

---

## 2. SSH Key Authentication

Switch to public/private key authentication for enhanced security.

### 2.1. Generate SSH Keys (Local Machine)

```sh
mkdir -p ~/.ssh
cd ~/.ssh
ssh-keygen -t rsa -b 4096 -C "Comment for the file"
```

### 2.2. Copy Public Key to Server

```sh
scp ~/.ssh/PUB_SSH_KEY_NAME.pub USER_NAME@IP_ADDRESS:/home/USER_NAME
```

### 2.3. Configure Server for Key Authentication

```sh
ssh USER_NAME@IP_ADDRESS
mv PUB_SSH_KEY_NAME.pub authorized_keys
mkdir -p ~/.ssh
mv authorized_keys ~/.ssh/
chmod 600 ~/.ssh/authorized_keys
sudo chattr +i ~/.ssh/authorized_keys
chmod 700 ~/.ssh
cd /etc/ssh
sudo nano sshd_config
# Ensure the following lines are set:
PubkeyAuthentication yes
AuthorizedKeysFile %h/.ssh/authorized_keys .ssh/authorized_keys2
PasswordAuthentication no
sudo systemctl restart ssh
```

### 2.4. Test SSH Key Login

```sh
ssh -i ~/.ssh/PRIVATE_SSH_KEY_NAME USER_NAME@IP_ADDRESS
```

---

---

## 3. SSH Config Alias (Local Machine)

Create an alias for easier login:

Edit `~/.ssh/config` and add:

```sh
Host myserver
    Hostname IP_ADDRESS
    User USER_NAME
    IdentityFile /path/to/private_key
    ServerAliveInterval 60
    ServerAliveCountMax 120
```

Now you can login with:

```sh
ssh myserver
```

---

---

## 4. System Updates & Firewall

### 4.1. Update & Upgrade

```sh
sudo apt update
sudo apt upgrade
sudo apt autoremove
```

### 4.2. Configure UFW Firewall

```sh
sudo apt install ufw
sudo ufw status verbose
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
# For app/database
sudo ufw allow 5432
# For Docker Swarm
sudo ufw allow 2377/tcp
sudo ufw allow 7946/tcp
sudo ufw allow 7946/udp
sudo ufw allow 4789/udp
# For GlusterFS
sudo ufw allow 24007/tcp
sudo ufw allow 24009:24024/tcp
sudo ufw allow 38465:38467/tcp
sudo ufw allow 49152:60999/tcp
# For TURN/STUN (Coturn)
sudo ufw allow 3478/udp     # STUN/TURN UDP
sudo ufw allow 3478/tcp     # TURN TCP fallback
sudo ufw allow 5349/tcp     # TURN over TLS (optional, enable when using SSL)
sudo ufw allow 20000:20100/udp  # TURN relay media ports

# For Janus Gateway
sudo ufw allow 8188/tcp     # Janus WebSocket
sudo ufw allow 8088/tcp     # Janus REST API (optional, may restrict to internal only)
sudo ufw allow 10000:10200/udp  # Janus RTP/RTCP media

sudo ufw enable
sudo reboot
```

---

---

## 5. Install & Configure fail2ban

```sh
sudo apt update
sudo apt install fail2ban
cd /etc/fail2ban
sudo cp jail.conf jail.local
sudo nano jail.local
# Set the following:
bantime = 604800s
findtime = 10800s
maxretry = 2
sudo systemctl restart fail2ban
```

**View fail2ban logs:**

```sh
cd /var/log
sudo cat fail2ban.log
```

**Unban your IP if needed:**

```sh
fail2ban-client set sshd unbanip IP_ADDRESS
```

---

---

## 6. Install Docker & Docker Compose

**Docker:** [Official Guide](https://docs.docker.com/engine/install/ubuntu/)

**Docker Compose:**

```sh
sudo apt update
sudo apt install docker-compose-plugin
docker compose version
```

**Add your user to the docker group:**

```sh
sudo groupadd docker
sudo usermod -aG docker USER_NAME
newgrp docker
docker run hello-world
```

---

---

## 7. Git Configuration & SSH for GitHub

**Set git config:**

```sh
sudo git config --global user.email "OWNER_OF_GITHUB_REPO_EMAIL"
git config --global user.email "OWNER_OF_GITHUB_REPO_EMAIL"
```

**Generate SSH keys for GitHub:**

```sh
ssh-keygen -t rsa -b 4096 -C "Comment for the file"
# Do not set a passphrase
# Copy the private key to your server's ~/.ssh folder
# Add the public key to your GitHub account
```

**Add to `~/.ssh/config` on the server:**

```sh
Host github.com
    User GIT_USER_NAME
    Hostname github.com
    IdentityFile ~/.ssh/github_rsa
```

**Test the connection:**

```sh
ssh -T git@github.com
```

---

---

## 8. Clone the Repository

```sh
cd /var
mkdir -p www/app
sudo chown USERNAME:USERNAME /var/www/app
cd /var/www/app
git clone SSH_REPO_URL .
```

---

## 9. Application Setup

### 9.1. Create Required Folders

```sh
mkdir -p ./api/vol/static/
mkdir -p ./api/vol/media/
mkdir -p ./db_backups/
mkdir -p ./volume_data/
```

### 9.2. Update Configuration Files

Update the following files from their sample files:

- `.env`
- `secrets/api/.env`
- `secrets/db/.env`
- `secrets/pgbouncer/.env`
- `client/next.config.js`
- `redis/redis.conf`
- `nginx/configs/default.conf`
- `init-letsencrypt.sh`
- `utils/assistances/backup_db_swarm.sh`

### 9.3. Set Executable Permissions

```sh
sudo chmod +x ./init-letsencrypt.sh
sudo chmod +x /var/www/app/utils/assistances/backup_db_swarm.sh
```

### 9.4. Setup HTTP Basic Auth for Flower (Optional)

```sh
sudo apt-get install apache2-utils
cd nginx
htpasswd -c .htpasswd CELERY_FLOWER_USER
# Use the CELERY_FLOWER_PASSWORD defined in your env variables
```

### 9.5. SSL Certificate Setup

1. Create the following folders:
   ```sh
   mkdir -p ./nginx/certbot/conf/
   mkdir -p ./nginx/certbot/www/
   ```
2. Add A records to your domain's DNS pointing to the server IP (including www as a CNAME).
3. Run the script:
   ```sh
   sudo ./init-letsencrypt.sh
   ```

### 9.6. Clean Up Docker (Optional)

```sh
docker container rm -f $(docker container ls -a -q)
docker image rm -f $(docker image ls -q)
docker volume rm $(docker volume ls -q)
```

### 9.7. Test SSL Setup

1. Update the domain in the server_name block of `default-temp-with-ssl.conf`.
2. Set permissions:
   ```sh
   sudo chown -R USERNAME:USERNAME /var/www/app
   ```
3. Start the app with SSL:
   ```sh
   sudo docker compose -f docker-compose-temp-with-ssl.yml up --build -d
   ```

### 9.8. Production Deployment

**With Compose:**

```sh
sudo docker compose -f docker-compose-prod.yml up --build -d
```

---

## 10. Docker Swarm & GlusterFS Deployment

### 10.1. Swarm Architecture Overview

- **Basic:** 1 Manager Node, 2 Worker Nodes
- **High Availability:** 3+ Manager Nodes (for quorum), 3+ Worker Nodes
- **(Recommended)**: Use a load balancer in front of your managers for production.

---

### 10.2. Swarm Cluster Setup

#### 10.2.1. Initialize Swarm on Manager

```sh
docker swarm init --advertise-addr <MANAGER_IP>
```

#### 10.2.2. Join Worker Nodes

On each worker node:

```sh
docker swarm join --token <WORKER_TOKEN> <MANAGER_IP>:2377
```

Get the join token from the manager:

```sh
docker swarm join-token worker
```

#### 10.2.3. Join Additional Manager Nodes (Optional)

On the primary manager node, get the manager token:

```sh
docker swarm join-token manager
```

On the new manager node:

```sh
docker swarm join --token <MANAGER_TOKEN> <MANAGER_IP>:2377
```

#### 10.2.4. Verify Cluster

On any manager node:

```sh
docker node ls
```

---

### 10.3. GlusterFS Setup

#### 10.3.1. Install GlusterFS on All Nodes

```sh
sudo apt update
sudo apt install glusterfs-server -y
sudo systemctl start glusterd
sudo systemctl enable glusterd
```

---

### 10.4. Onboarding a New Node to GlusterFS Cluster

#### 1. Prepare the New Node

```sh
sudo mkdir -p /gluster/brick1
sudo chown -R <USER>:<USER> /gluster
```

#### 2. Add the New Node to the Cluster (from any existing node)

```sh
sudo gluster peer probe <NEW_NODE_IP>
```

#### 3. (If needed) Update the Volume to Include the New Node

If expanding the replica set, create or expand the volume as needed:

```sh
sudo gluster volume create app-volume replica <REPLICA_COUNT> \
  <NODE1_IP>:/gluster/brick1 \
  <NODE2_IP>:/gluster/brick1 \
  ... \
  force
sudo gluster volume start app-volume
sudo gluster volume info
```

#### 4. Mount the GlusterFS Volume on the New Node

```sh
sudo apt install glusterfs-client -y
sudo mkdir -p /var/www/app
sudo chown <USER>:<USER> /var/www/app
sudo mount -t glusterfs <NEW_NODE_IP>:/app-volume /var/www/app
```

##### (Optional) Auto-mount on Boot

Add to `/etc/fstab`:

```
<NEW_NODE_IP>:/app-volume /var/www/app glusterfs defaults,_netdev 0 0
```

##### (Optional) Systemd Service for Mounting

Create `/etc/systemd/system/mount-glusterfs.service`:

```ini
[Unit]
Description=Mount GlusterFS Volume
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/mount -a
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

Enable the service:

```sh
sudo systemctl enable mount-glusterfs.service
```

---

### 10.5. GlusterFS Watchdog Service

Create `/etc/systemd/system/glusterfs-watchdog.service`:

```ini
[Unit]
Description=GlusterFS Watchdog
After=network.target

[Service]
ExecStart=/var/www/app/glusterfs_watchdog.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

Reload and enable the service:

```sh
sudo systemctl daemon-reload
sudo systemctl enable glusterfs-watchdog
sudo systemctl start glusterfs-watchdog
```

(Optional) Create a log file for the watchdog script:

```sh
sudo touch /var/log/glusterfs_watchdog.log
sudo chmod 666 /var/log/glusterfs_watchdog.log
```

---

### 10.6. Useful Docker Swarm Commands

- **List nodes:**
  ```sh
  docker node ls
  ```
- **Inspect node:**
  ```sh
  docker node inspect <NODE_ID>
  ```
- **Remove node:**
  ```sh
  docker node rm <NODE_ID>
  ```
- **Leave swarm:**
  ```sh
  docker swarm leave [--force]
  ```
- **List services:**
  ```sh
  docker service ls
  ```
- **List tasks of a service:**
  ```sh
  docker service ps <service_name>
  ```
- **Logs:**
  ```sh
  docker service logs <service_name>
  docker logs <container_id>
  ```
- **Scale a service:**
  ```sh
  docker service scale <service_name>=<replicas>
  ```
- **Update node availability:**
  ```sh
  docker node update --availability drain|active <NODE_ID>
  ```

---

## 11. Continuous Integration & Continuous Deployment (CI/CD)

CI/CD (Continuous Integration and Continuous Deployment) is a set of practices that automate the process of integrating code changes, testing, and deploying applications. This ensures that new features, bug fixes, and updates can be delivered to users quickly, reliably, and with minimal manual intervention. In this project, you can use the provided automation script to streamline your deployment process.

### Deploying with automation.sh

1. Update variables in `utils/shellScripting/constants`:
   ```sh
   PROD_SERVER_ALIAS=PROD_SERVER_ALIAS
   NGINX_REPO="NGINX_REPO_ON_DOCKER_HUB"
   CLIENT_REPO="CLIENT_REPO_ON_DOCKER_HUB"
   API_REPO="API_REPO_ON_DOCKER_HUB"
   ```
2. Run `automation.sh` in the root folder and follow the prompts to deploy your application.

---

#### Automated Maintenance (SSL Renewal, Sitemap, and Backups)

To ensure SSL certificates are auto-renewed, sitemaps are generated, and database backups are performed regularly, add the following to `sudo crontab -e`:

```cron
0 1 * * * /var/www/app/utils/assistances/generate_sitemap.sh
0 2 * * * /var/www/app/utils/assistances/backup_db_swarm.sh
0 3 * * * /var/www/app/utils/assistances/update_nginx.sh
0 4 * * * docker system prune -a --volumes
```

These scheduled tasks will keep your SSL certificates up to date, generate sitemaps for SEO, and back up your database automatically.

---

Your application should now be securely deployed and production-ready!
