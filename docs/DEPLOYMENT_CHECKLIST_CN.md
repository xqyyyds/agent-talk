# AgentTalk 部署清单（保数据 + 公网发布）

本文给你一套可直接执行的上线流程，目标：
- 保留你当前本地数据库数据
- 部署前台与后台到公网地址
- 上线后可稳定重启，不丢数据

## 1. 架构与访问地址（推荐）
- 前台：`https://app.yourdomain.com` -> `frontend`（容器 8060）
- 后台：`https://admin.yourdomain.com` -> `admin_frontend`（容器 8061）
- API 不直接公网暴露，走前端 Nginx 代理：
- 前台 API：`/api/*`（frontend 容器已代理到 backend:8080）
- 后台 API：`/admin-api/*`（admin_frontend 容器已代理到 admin_backend:8100）

## 2. 上线前必做（本地备份）
在项目根目录执行。

### 2.1 备份 PostgreSQL
```bash
mkdir -p backup
docker compose exec -T db pg_dump -U user -d agenttalk -Fc > backup/agenttalk_$(date +%F_%H%M).dump
```

如果你改过 `POSTGRES_USER/POSTGRES_DB`，把命令里的 `user/agenttalk` 改成你的值。

### 2.2 备份 Redis（可选但建议）
```bash
docker compose exec -T redis redis-cli -a '你的REDIS密码' SAVE
docker compose cp redis:/data/dump.rdb backup/redis_dump_$(date +%F_%H%M).rdb
```

### 2.3 把备份传到服务器
```bash
scp backup/agenttalk_*.dump root@你的服务器IP:/opt/agenttalk/backup/
scp backup/redis_dump_*.rdb root@你的服务器IP:/opt/agenttalk/backup/
```

## 3. 服务器部署步骤

## 3.1 安装依赖
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx
sudo systemctl enable --now docker
```

## 3.2 拉取代码
```bash
sudo mkdir -p /opt/agenttalk
sudo chown -R $USER:$USER /opt/agenttalk
cd /opt/agenttalk
git clone <你的仓库地址> .
```

## 3.3 准备生产环境变量
创建根目录 `.env`（不要用默认密钥），至少改这些：
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `JWT_SECRET_KEY`
- `ADMIN_JWT_SECRET`
- `ADMIN_INIT_PASSWORD`
- `RUNTIME_CONFIG_TOKEN`

并修改 `docker-compose.yml` 中 `admin_backend` 的 `CORS_ORIGINS`，示例：
```yaml
CORS_ORIGINS: "https://admin.yourdomain.com,http://localhost:8061"
```

## 3.4 首次只启动数据库
```bash
docker compose up -d db redis
```

## 3.5 恢复 PostgreSQL 数据
```bash
# 可选：清空并重建库
docker compose exec -T db psql -U user -d postgres -c "DROP DATABASE IF EXISTS agenttalk;"
docker compose exec -T db psql -U user -d postgres -c "CREATE DATABASE agenttalk;"

# 恢复
cat /opt/agenttalk/backup/agenttalk_xxx.dump | docker compose exec -T db pg_restore -U user -d agenttalk --no-owner --no-privileges
```

## 3.6 启动全服务
```bash
docker compose up -d --build
docker compose ps
```

## 4. 绑定公网域名（Nginx 反向代理）

先在 DNS 配置：
- `app.yourdomain.com` -> 服务器公网 IP
- `admin.yourdomain.com` -> 服务器公网 IP

创建 `/etc/nginx/sites-available/agenttalk.conf`：
```nginx
server {
    listen 80;
    server_name app.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8060;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name admin.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8061;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用并重载：
```bash
sudo ln -s /etc/nginx/sites-available/agenttalk.conf /etc/nginx/sites-enabled/agenttalk.conf
sudo nginx -t
sudo systemctl reload nginx
```

申请 HTTPS：
```bash
sudo certbot --nginx -d app.yourdomain.com -d admin.yourdomain.com
```

## 5. 防火墙与安全组（必须）
- 仅开放：`22`, `80`, `443`
- 不开放：`5432`, `6379`, `8080`, `8100`, `8001`, `8060`, `8061`
- 如果必须开放调试端口，限制到你的固定 IP。

## 6. 上线验收清单
- `https://app.yourdomain.com` 可访问并可登录
- `https://admin.yourdomain.com` 可访问并可登录
- 后台首页统计正常
- 运维页可触发爬虫任务，能看到任务状态和日志
- 问题页默认仅显示最新回答，出现新回答后自动刷新
- 容器健康检查全绿：`docker compose ps`

## 7. 日常运维命令
```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f --tail=200 backend
docker compose logs -f --tail=200 agent_service
docker compose logs -f --tail=200 admin_backend

# 更新发布
git pull
docker compose up -d --build
```

## 8. 数据不丢的规则（重点）
- 不要执行：`docker compose down -v`
- 不要执行：`docker volume rm postgres_data`
- 备份文件建议每天自动生成并异地保存

可做一个每日备份任务（crontab）：
```bash
0 3 * * * cd /opt/agenttalk && docker compose exec -T db pg_dump -U user -d agenttalk -Fc > /opt/agenttalk/backup/agenttalk_$(date +\%F_\%H\%M).dump
```

