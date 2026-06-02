# Skill Seekers 操作手册

这份手册覆盖完整流程：

`本地资料 -> 阿里云 Ubuntu ECS -> Skill Seekers 生成 skill -> 打包 -> 在本地/IntelliJ IDEA/Hermes 中使用与部署`

适合你的这类资料型输入，尤其是 `.docx` 文档集合。

## 1. 环境准备

目标服务器建议使用 `Ubuntu 22.04/24.04`。

登录服务器：

```bash
ssh root@你的ECS公网IP
```

安装基础环境：

```bash
apt update
apt install -y python3 python3-pip python3-venv git unzip pandoc
```

创建工作目录并安装 Skill Seekers：

```bash
mkdir -p /opt/skillseekers/workspace
cd /opt/skillseekers
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install skill-seekers
skill-seekers --help
```

建议目录结构：

```text
/opt/skillseekers
  /.venv
  /workspace
  /output
```

## 2. 上传本地资料到 ECS

如果你用 `Xftp`，把本地资料上传到：

```text
/opt/skillseekers/workspace/
```

例如上传后变成：

```text
/opt/skillseekers/workspace/100+AI指令合集
```

如果你用本机 `scp`，在 Windows 本机执行：

```powershell
scp -r "D:\你的资料目录" root@你的ECS公网IP:/opt/skillseekers/workspace/
```

检查上传结果：

```bash
ls -lah /opt/skillseekers/workspace
```

## 3. 把 `.docx` 批量转成 `.md`

`Skill Seekers` 更适合处理 `Markdown/代码/配置/文本`，不建议直接拿一堆 `.docx` 原件去生成 skill。

创建转换目录：

```bash
mkdir -p "/opt/skillseekers/workspace/ai-prompts-md"
```

批量转换：

```bash
find "/opt/skillseekers/workspace/100+AI指令合集" -name "*.docx" | while read f; do out="/opt/skillseekers/workspace/ai-prompts-md/${f#/opt/skillseekers/workspace/100+AI指令合集/}"; out="${out%.docx}.md"; mkdir -p "$(dirname "$out")"; pandoc "$f" -t markdown -o "$out"; done
```

检查转换结果：

```bash
find "/opt/skillseekers/workspace/ai-prompts-md" -type f | head -30
```

## 4. 生成 skill

进入工作目录并激活虚拟环境：

```bash
cd /opt/skillseekers
source .venv/bin/activate
```

执行生成：

```bash
skill-seekers create "./workspace/ai-prompts-md"
```

生成成功后，主要产物通常在：

```text
/opt/skillseekers/output/ai-prompts-md/
  SKILL.md
  references/
  code_analysis.json
```

检查结果：

```bash
ls -lah /opt/skillseekers/output/ai-prompts-md
```

说明：

- 如果出现 `Command not found: claude`，通常只是可选增强步骤没执行，不影响主产物生成。
- 如果日志里显示找到了很多 `markdown files`，说明资料已经被正常识别。

## 5. 打包 skill

打包成 OpenAI 目标格式：

```bash
skill-seekers package "./output/ai-prompts-md" --target openai
```

如果终端出现：

```text
Continue with packaging? (y/n):
```

输入：

```bash
y
```

打包成功后，通常会得到：

```text
/opt/skillseekers/output/ai-prompts-md-openai.zip
```

检查所有产物：

```bash
find /opt/skillseekers/output -maxdepth 3 -type f | sort
```

## 6. 下载产物回本地

在 Windows 本机执行：

```powershell
scp root@你的ECS公网IP:/opt/skillseekers/output/ai-prompts-md-openai.zip "D:\skill_output\"
```

如果用 `Xftp`，到服务器目录：

```text
/opt/skillseekers/output/
```

下载：

```text
ai-prompts-md-openai.zip
```

## 7. skill 产物说明

你这次会得到两类产物：

1. 原始 skill 目录

```text
output/ai-prompts-md/
```

里面包含：

- `SKILL.md`
- `references/`
- 其他分析文件

2. 打包后的目标文件

```text
output/ai-prompts-md-openai.zip
```

使用建议：

- 给 `Hermes`、本地知识库、IDEA 项目使用：优先用原始目录里的 `SKILL.md + references/`
- 给 OpenAI / Custom GPT 类场景：使用 `openai.zip`

## 8. 在 IntelliJ IDEA 里使用

IDEA 不会自动安装这个 skill。最好的方式是把它当成项目知识库。

推荐目录：

```text
your-project/
  docs/
    skills/
      ai-prompts/
        SKILL.md
        references/
```

把服务器产物中的：

- `SKILL.md`
- `references/`

复制到这里。

推荐再加一个说明文件：

```text
docs/skills/ai-prompts/README.md
```

在 IDEA 里使用时，对 AI 助手明确说：

```text
先阅读 docs/skills/ai-prompts/SKILL.md，再按其中规则回答。
```

或者：

```text
参考 docs/skills/ai-prompts/references/ 下的资料，帮我整理成……
```

推荐调用模板：

```text
先阅读 docs/skills/ai-prompts/SKILL.md，
再参考 docs/skills/ai-prompts/references/，
然后帮我完成：……
```

## 9. 在 Hermes 里部署

Hermes 更适合直接使用技能目录，不是 `openai.zip`。

目标目录：

```text
~/.hermes/skills/技能名/
```

例如部署为：

```text
~/.hermes/skills/ai-prompts-md/
  SKILL.md
  references/
```

在 ECS 上执行：

```bash
mkdir -p ~/.hermes/skills/ai-prompts-md
cp /opt/skillseekers/output/ai-prompts-md/SKILL.md ~/.hermes/skills/ai-prompts-md/
cp -r /opt/skillseekers/output/ai-prompts-md/references ~/.hermes/skills/ai-prompts-md/
find ~/.hermes/skills/ai-prompts-md -maxdepth 2 -type f
```

部署后重启 Hermes，或开启新的 Hermes 会话，让它重新扫描技能目录。

如果 Hermes 支持按技能名调用，通常就可以这样使用：

```text
/ai-prompts-md 帮我生成一组适合知识付费短视频的中文提示词
```

## 10. 推荐的复用模板

以后你只需要替换这 4 个变量：

- `你的ECS公网IP`
- `你的资料目录`
- `转换后目录`
- 本地下载目录

核心复用流程：

```bash
cd /opt/skillseekers
source .venv/bin/activate
mkdir -p "/opt/skillseekers/workspace/转换后目录"
find "/opt/skillseekers/workspace/你的资料目录" -name "*.docx" | while read f; do out="/opt/skillseekers/workspace/转换后目录/${f#/opt/skillseekers/workspace/你的资料目录/}"; out="${out%.docx}.md"; mkdir -p "$(dirname "$out")"; pandoc "$f" -t markdown -o "$out"; done
skill-seekers create "./workspace/转换后目录"
skill-seekers package "./output/转换后目录" --target openai
```

## 11. 常见问题

`scp` 上传报 `Could not resolve hostname d`

原因：你在服务器里执行了 Windows 路径的 `scp`。

处理：上传命令必须在你自己的 Windows 本机执行。

`skill-seekers create` 提示 `Found 0 source files`

这通常不是失败，而是输入目录里没有代码文件。

如果是资料型输入，重点看它是否找到了 `markdown files`。

出现 `Command not found: claude`

说明可选 AI 增强没跑，不影响 `SKILL.md` 和 `references/` 的主产物生成。

`package` 阶段被取消

通常是因为提示：

```text
Continue with packaging? (y/n):
```

你没有输入 `y`。

## 12. 最佳实践

- 资料型输入优先走：`.docx -> .md -> create -> package`
- 给 IDE/Hermes 用，优先使用 `SKILL.md + references/`
- 给 OpenAI 场景用，再生成 `openai.zip`
- skill 名尽量用英文目录名，长期更稳
- 同一类资料放一个 skill，别把完全不同主题混在一起

## 参考

- [Skill Seekers GitHub](https://github.com/yusufkaraaslan/Skill_Seekers)
- [Skill Seekers PyPI](https://pypi.org/project/skill-seekers/)
- [Hermes Skills 文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/)
- [IntelliJ IDEA Markdown 文档](https://www.jetbrains.com/help/idea/markdown.html)
