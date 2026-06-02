# Hermes `systemd` 常驻配置

下面这份配置适用于大多数 Ubuntu ECS 场景，目标是让 `Hermes` 在服务器上常驻运行，并在重启后自动拉起。

## 1. 先确认两个参数

先在服务器上执行：

```bash
whoami
which hermes
```

你需要记下：

- 运行用户，例如 `root` 或 `ubuntu`
- `hermes` 可执行文件路径，例如 `/root/.local/bin/hermes`

## 2. 服务文件模板

参考 [hermes.service.example](/D:/codex/hermes.service.example)：

```ini
[Unit]
Description=Hermes Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/root/.local/bin/hermes
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

如果你的用户不是 `root`，或者 `hermes` 不在 `/root/.local/bin/hermes`，把这两处替换掉即可。

## 3. 安装为系统服务

在 ECS 上创建服务文件：

```bash
sudo cp /path/to/hermes.service /etc/systemd/system/hermes.service
```

或者直接编辑：

```bash
sudo nano /etc/systemd/system/hermes.service
```

粘贴服务内容后，执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable hermes
sudo systemctl start hermes
sudo systemctl status hermes
```

## 4. 常用管理命令

启动：

```bash
sudo systemctl start hermes
```

停止：

```bash
sudo systemctl stop hermes
```

重启：

```bash
sudo systemctl restart hermes
```

查看状态：

```bash
sudo systemctl status hermes
```

查看日志：

```bash
sudo journalctl -u hermes -f
```

## 5. 常见调整

如果 `systemd` 里提示找不到命令，通常是 `ExecStart` 路径不对，重新检查：

```bash
which hermes
```

如果 Hermes 依赖虚拟环境或用户级安装路径，可以在服务里补上 `PATH`：

```ini
Environment="PATH=/root/.local/bin:/usr/local/bin:/usr/bin:/bin"
```

如果你想让它以 `ubuntu` 用户运行，改成：

```ini
User=ubuntu
WorkingDirectory=/home/ubuntu
ExecStart=/home/ubuntu/.local/bin/hermes
```

## 6. 推荐做法

- 长期使用 ECS：优先 `systemd`
- 临时调试：用 `tmux`
- 不建议长期只靠 `nohup`

## 7. 最小可执行步骤

如果你想最快跑通，只要按这个顺序来：

```bash
whoami
which hermes
sudo nano /etc/systemd/system/hermes.service
sudo systemctl daemon-reload
sudo systemctl enable hermes
sudo systemctl start hermes
sudo systemctl status hermes
```
