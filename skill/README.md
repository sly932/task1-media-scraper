# media-scraper Claude Code Skill

装上后，你可以用**自然语言**让 Claude Code 操控本工具：启动、跑查询、调阈值/权重，无需记命令。

## 安装

把 `media-scraper/` 目录放到你的 Claude Code skills 目录：

```bash
# 方式一：直接用本目录里的 zip
unzip media-scraper-skill.zip -d ~/.claude/skills/

# 方式二：拷贝目录
cp -r media-scraper ~/.claude/skills/
```

重开一个 Claude Code 会话即可生效。

## 用法

直接说人话，例如：

- 「启动 media-scraper」 / 「打开那个采集工具的网页」
- 「跑一下采集，找做增肌餐方向的创作者」
- 「把粉丝门槛提到 50 万」 / 「返回 10 条」
- 「结果不太相关，调一下排序权重」

Claude 会自动定位项目、选对运行挡位、改 `config.yaml` 并重跑验证。

> 首次使用时它会问你 `task1-media-scraper` 的实际路径（或自动定位），并确认 `.env` 里的 key 已填好。
