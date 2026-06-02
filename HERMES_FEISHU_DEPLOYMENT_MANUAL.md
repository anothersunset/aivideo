# Hermes 飞书接入与常驻服务操作手册

本文面向这样的目标：

- 在云服务器上为 `Hermes` 配置飞书机器人
- 让机器人服务长期在线
- 服务器重启后自动恢复
- 能快速排查常见故障

本文基于一套已经跑通的实践整理，适用于 Ubuntu 类 Linux 云服务器。

## 1. 目标说明

最终我们要实现的是：

- Hermes 能成功连接飞书
- 在飞书里给机器人发消息后，Hermes 能收到并回复
- Hermes Gateway 作为系统服务常驻运行

需要特别注意：

- `hermes` 是 CLI/TUI 交互入口，不适合直接作为后台机器人服务运行
- 真正应该常驻运行的是 `hermes-gateway`

## 2. 环境前提

确保你已经具备下面条件：

- 一台可以联网的云服务器
- 已安装 Hermes
- 已在飞书开放平台创建应用/机器人
- 已拿到飞书机器人的 `App ID` 和 `App Secret`

如果你当前登录用户是 `root`，可先确认：

```bash
whoami
```

预期输出：

```text
root
```

## 3. 确认 Hermes 安装路径

先确认 Hermes 命令和相关目录：

```bash
which hermes
find /root -maxdepth 3 \( -name "hermes" -o -name "hermes*" \) 2>/dev/null
ls -lah /root/hermes-agent
```

在实际跑通的环境中，关键路径如下：

```text
/root/.local/bin/hermes
/root/hermes-agent
/root/.hermes/hermes-agent/venv/bin/python3
```

其中：

- `/root/.local/bin/hermes` 是 Hermes 命令入口
- `/root/hermes-agent` 是项目目录
- `/root/.hermes/hermes-agent/venv/bin/python3` 是带 Hermes 依赖的 Python 环境

## 4. 不要把 `hermes` 当成飞书后台服务

很多人会先尝试把下面命令做成 `systemd` 服务：

```bash
hermes
```

或者：

```bash
/root/.local/bin/hermes
```

这样做通常会失败，因为它是交互式程序。典型日志如下：

```text
Warning: Input is not a terminal (fd=0).
Goodbye!
```

这表示：

- 当前启动的是 CLI/TUI
- 它需要终端交互
- 不能直接作为飞书机器人后台服务使用

正确做法是使用：

```bash
/root/hermes-agent/scripts/hermes-gateway
```

## 5. 找到正确的服务入口

查看 `scripts/hermes-gateway` 内容：

```bash
cd /root/hermes-agent
sed -n '1,220p' scripts/hermes-gateway
```

这里会明确说明：

```text
Hermes Gateway - Standalone messaging platform integration.
This is the proper entry point for running the gateway as a service.
NOT tied to the CLI - runs independently.
```

这就确认了：

- 飞书、Telegram、Discord 等消息平台接入应该使用 `hermes-gateway`
- 不应该拿 `hermes` CLI 当守护服务

## 6. 配置飞书环境变量

Hermes 会从 `~/.hermes/.env` 读取飞书配置。

先创建或编辑该文件：

```bash
mkdir -p ~/.hermes
nano ~/.hermes/.env
```

建议最小配置如下：

```env
FEISHU_DOMAIN=feishu
FEISHU_CONNECTION_MODE=websocket
FEISHU_APP_ID=你的飞书AppID
FEISHU_APP_SECRET=你的飞书AppSecret
FEISHU_ALLOW_ALL_USERS=true
FEISHU_GROUP_POLICY=open
FEISHU_HOME_CHANNEL=hermes gateway
```

说明：

- `FEISHU_DOMAIN=feishu`
  指定飞书环境
- `FEISHU_CONNECTION_MODE=websocket`
  使用 websocket 与飞书连接
- `FEISHU_APP_ID`
  飞书应用的 App ID
- `FEISHU_APP_SECRET`
  飞书应用的 App Secret
- `FEISHU_ALLOW_ALL_USERS=true`
  测试阶段允许所有用户调用机器人
- `FEISHU_GROUP_POLICY=open`
  允许群聊使用

如果你后续要收紧权限，可改为：

```env
FEISHU_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=你的飞书用户ID
```

## 7. 确认飞书依赖安装在哪个 Python 环境

Hermes Gateway 很依赖正确的 Python 环境。

先测试系统 Python 是否安装了飞书 SDK：

```bash
python3 -c "import lark_oapi; print('ok')"
```

如果输出：

```text
ModuleNotFoundError: No module named 'lark_oapi'
```

不要慌，这通常说明系统 Python 没装该包。

再测试 Hermes 自己的 Python 环境：

```bash
/root/.hermes/hermes-agent/venv/bin/python3 -c "import lark_oapi; print('ok')"
```

如果输出：

```text
ok
```

说明：

- `lark_oapi` 安装在 Hermes 自己的虚拟环境里
- 之后启动 Gateway 必须使用这个 Python

## 8. 手工前台测试飞书连接

不要直接运行：

```bash
./scripts/hermes-gateway run
```

因为脚本头通常是：

```text
#!/usr/bin/env python3
```

这会优先使用系统 `python3`，从而进入错误环境。

正确测试命令：

```bash
/root/.hermes/hermes-agent/venv/bin/python3 /root/hermes-agent/scripts/hermes-gateway run
```

如果配置正确，你会看到类似输出：

```text
Starting Hermes Gateway...
Press Ctrl+C to stop.
[Lark] ... connected to wss://msg-frontier.feishu.cn/ws/v2...
```

只要看到 `connected to wss://msg-frontier.feishu.cn/ws/v2`，就说明：

- 飞书凭证生效了
- `lark_oapi` 可用
- Gateway 已成功连上飞书

## 9. 验证机器人是否能回复

在 Gateway 保持前台运行时：

1. 打开飞书
2. 给机器人发一条简单消息，比如 `ping`
3. 观察终端输出

如果有收发记录，说明链路已打通。

如果连接成功但没有回复，优先检查：

- `FEISHU_ALLOW_ALL_USERS`
- `FEISHU_ALLOWED_USERS`
- 群聊策略

测试阶段建议：

```env
FEISHU_ALLOW_ALL_USERS=true
```

## 10. 配置为系统常驻服务

飞书机器人跑通后，再配置成 `systemd` 服务。

创建服务文件：

```bash
cat >/etc/systemd/system/hermes-gateway.service <<'EOF'
[Unit]
Description=Hermes Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/hermes-agent
Environment=HOME=/root
ExecStart=/root/.hermes/hermes-agent/venv/bin/python3 /root/hermes-agent/scripts/hermes-gateway run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

加载并启动：

```bash
systemctl daemon-reload
systemctl enable hermes-gateway
systemctl start hermes-gateway
systemctl status hermes-gateway
```

预期状态类似：

```text
Loaded: loaded (/etc/systemd/system/hermes-gateway.service; enabled; ...)
Active: active (running)
```

## 11. 查看实时日志

运行中最常用的排查命令：

```bash
journalctl -u hermes-gateway -f
```

查看最近日志：

```bash
journalctl -u hermes-gateway -n 50 --no-pager
```

常用管理命令：

```bash
systemctl status hermes-gateway
systemctl restart hermes-gateway
systemctl stop hermes-gateway
systemctl is-enabled hermes-gateway
```

## 12. 验证是否真正“始终在线”

你需要验证 4 件事：

1. 服务是运行中的

```bash
systemctl status hermes-gateway
```

2. 服务已开机自启

```bash
systemctl is-enabled hermes-gateway
```

3. 日志中有飞书连接记录

```bash
journalctl -u hermes-gateway -n 50 --no-pager
```

4. 飞书里实时发消息，机器人能回复

同时开一个窗口看日志：

```bash
journalctl -u hermes-gateway -f
```

然后在飞书发送测试消息。

## 13. 服务器重启后的验证

为了确认“始终连接”确实成立，可以做一次完整演练。

在服务器上执行：

```bash
reboot
```

服务器重启后重新登录，再检查：

```bash
systemctl status hermes-gateway
journalctl -u hermes-gateway -n 50 --no-pager
```

最后再去飞书发一条测试消息。

如果服务自动恢复且机器人依然能回复，就说明常驻成功。

## 14. 常见错误与改正方法

### 错误 1：把 `hermes` 当成后台服务运行

现象：

```text
Warning: Input is not a terminal (fd=0).
Goodbye!
```

原因：

- 启动了交互式 CLI
- `systemd` 没有终端交互环境

改正方法：

- 不要运行 `hermes`
- 改用 `hermes-gateway`

正确命令：

```bash
/root/.hermes/hermes-agent/venv/bin/python3 /root/hermes-agent/scripts/hermes-gateway run
```

### 错误 2：运行 `./scripts/hermes-gateway run` 后提示飞书依赖缺失

现象：

```text
WARNING gateway.run: Feishu: lark-oapi not installed or FEISHU_APP_ID/SECRET not set
WARNING gateway.run: No adapter available for feishu
```

原因：

- 脚本通过 `#!/usr/bin/env python3` 使用了系统 Python
- 系统 Python 没有 `lark_oapi`

改正方法：

- 强制使用 Hermes 自己的 Python 环境启动

正确命令：

```bash
/root/.hermes/hermes-agent/venv/bin/python3 /root/hermes-agent/scripts/hermes-gateway run
```

### 错误 3：系统 Python 里没有 `lark_oapi`

现象：

```bash
python3 -c "import lark_oapi; print('ok')"
```

输出：

```text
ModuleNotFoundError: No module named 'lark_oapi'
```

原因：

- 飞书 SDK 没装在系统 Python 中

改正方法：

- 不要盲目依赖系统 Python
- 优先使用 Hermes 自己的 venv

验证命令：

```bash
/root/.hermes/hermes-agent/venv/bin/python3 -c "import lark_oapi; print('ok')"
```

### 错误 4：飞书连接不上

现象：

```text
WARNING gateway.run: Feishu: lark-oapi not installed or FEISHU_APP_ID/SECRET not set
ERROR gateway.run: Gateway failed to connect any configured messaging platform
```

原因：

- `FEISHU_APP_ID` 未配置
- `FEISHU_APP_SECRET` 未配置
- 配置文件未被读取

改正方法：

检查：

```bash
grep -n "FEISHU_" ~/.hermes/.env
```

确保至少存在：

```env
FEISHU_APP_ID=你的飞书AppID
FEISHU_APP_SECRET=你的飞书AppSecret
```

### 错误 5：已经连接飞书，但发消息没有回复

现象：

- 日志已显示连接成功
- 飞书机器人不回复消息

原因：

- 权限策略阻止了当前用户
- 开了白名单但没有填允许用户

典型错误配置：

```env
FEISHU_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=
```

这等于拒绝所有用户。

改正方法：

测试阶段先用：

```env
FEISHU_ALLOW_ALL_USERS=true
```

正式环境再改成：

```env
FEISHU_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=你的飞书用户ID
```

### 错误 6：在 shell 里误把 `ExecStart=...` 当命令执行

错误示例：

```bash
ExecStart=/root/.hermes/hermes-agent/venv/bin/python3 /root/hermes-agent/scripts/hermes-gateway run
```

原因：

- 这是 shell 环境变量赋值，不是你想要的启动方式
- 实际执行的仍可能是脚本自己的 shebang 环境

改正方法：

手工测试时直接运行完整命令：

```bash
/root/.hermes/hermes-agent/venv/bin/python3 /root/hermes-agent/scripts/hermes-gateway run
```

只有在 `systemd` 服务文件里才写：

```ini
ExecStart=/root/.hermes/hermes-agent/venv/bin/python3 /root/hermes-agent/scripts/hermes-gateway run
```

### 错误 7：配置了服务，但机器人仍不在线

现象：

- 服务文件存在
- 飞书不响应

排查方法：

先检查状态：

```bash
systemctl status hermes-gateway
```

再看日志：

```bash
journalctl -u hermes-gateway -f
```

重点看：

- 是否成功启动
- 是否连接到飞书 websocket
- 是否收到消息事件

## 15. 推荐的最终配置策略

测试环境建议：

```env
FEISHU_DOMAIN=feishu
FEISHU_CONNECTION_MODE=websocket
FEISHU_APP_ID=你的飞书AppID
FEISHU_APP_SECRET=你的飞书AppSecret
FEISHU_ALLOW_ALL_USERS=true
FEISHU_GROUP_POLICY=open
FEISHU_HOME_CHANNEL=hermes gateway
```

正式环境建议：

```env
FEISHU_DOMAIN=feishu
FEISHU_CONNECTION_MODE=websocket
FEISHU_APP_ID=你的飞书AppID
FEISHU_APP_SECRET=你的飞书AppSecret
FEISHU_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=你的飞书用户ID
FEISHU_GROUP_POLICY=open
FEISHU_HOME_CHANNEL=hermes gateway
```

## 16. 最小可执行清单

如果你想快速复现整套流程，只按下面顺序执行即可：

1. 准备 `~/.hermes/.env`
2. 确认 Hermes venv 可用
3. 用正确 Python 前台运行 `hermes-gateway`
4. 在飞书里测试收发
5. 配置 `systemd`
6. 重启服务并观察日志
7. 重启服务器后再次验证

关键命令汇总：

```bash
/root/.hermes/hermes-agent/venv/bin/python3 -c "import lark_oapi; print('ok')"
/root/.hermes/hermes-agent/venv/bin/python3 /root/hermes-agent/scripts/hermes-gateway run
systemctl daemon-reload
systemctl enable hermes-gateway
systemctl start hermes-gateway
systemctl status hermes-gateway
journalctl -u hermes-gateway -f
```

## 17. 结论

要让 Hermes 在云服务器上稳定接入飞书并始终在线，核心原则只有三条：

1. 不要运行 `hermes` CLI，当守护服务时必须运行 `hermes-gateway`
2. 不要依赖系统 `python3`，要使用 Hermes 自己带依赖的 Python 环境
3. 先前台跑通，再交给 `systemd` 常驻

只要这三点不偏，飞书机器人服务一般都能稳定落地。
