<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-random

_✨ Nonebot2 通用抽图/语音插件 ✨_

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/jcjrobert/nonebot-plugin-random.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-random">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-random.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.9.5+-blue.svg" alt="python">

</div>

## 📖 介绍

`nonebot-plugin-random` 是面向 NoneBot2 和 OneBot V11 的通用随机素材插件。只需在 `data/random` 中建立资源池并放入素材，即可提供文本、图片、语音或视频随机抽取功能。

0.1.0 新增动态资源池管理、网页截图面板、群级与全局开关、群级冷却、跨群管理、资源池归档恢复和严格配置校验。资源池 Matcher 可以在运行期间创建、重建或注销，无需每次修改后重启机器人。

## 💿 安装

插件要求 Python 3.9.5 或更高版本。

使用 nb-cli：

```shell
nb plugin install nonebot-plugin-random
```

使用 pip：

```shell
pip install nonebot-plugin-random
```

然后在 NoneBot2 配置中加载插件，或在入口文件中调用：

```python
nonebot.load_plugin("nonebot-plugin-random")
```

管理面板由 `nonebot-plugin-htmlrender` 渲染。首次部署时请按照该插件的说明准备 Playwright 浏览器运行环境；浏览器不可用时，随机池列表会回退为文本消息。

## 🎉 快速开始

机器人启动时会创建并扫描运行目录下的 `data/random/`。每个不以 `.` 或 `_` 开头的子目录都是一个资源池，例如：

```text
data/
├─ random/
│  ├─ capoo/
│  │  ├─ config.json
│  │  ├─ happy.png
│  │  └─ nested/
│  │     └─ sleepy.webp
│  └─ quote/
│     ├─ config.json
│     └─ hello.txt
└─ random_archive/
```

若 `capoo` 没有 `config.json`，插件会使用默认配置并注册 `随机capoo` 命令。已有的 `data/random/<资源池>` 目录可以继续使用，但新版配置采用严格校验；包含未知字段、错误类型或非法值的资源池会记录错误并跳过。

## ⚙️ 资源池配置

`config.json` 必须是 UTF-8 编码的 JSON 对象。

```json
{
    "display_name": "Capoo",
    "draw_output": "image",
    "draw_mode": "direct",
    "cooldown_seconds": 10,
    "message_type": "command",
    "message": ["随机capoo"],
    "insert_message": ["添加随机capoo"],
    "delete_message": ["删除随机capoo"],
    "modify_admin_only": true,
    "is_tome": false,
    "output_prefix": "",
    "output_suffix": "",
    "is_at_sender": false
}
```

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `display_name` | 当前目录名 | 展示名称，最多 30 个字符 |
| `draw_output` | `image` | 输出类型：`text`、`image`、`record` 或 `video` |
| `draw_mode` | `direct` | `direct` 从资源池全部子目录递归抽取；`indirect` 先等概率选择一个一级子目录，再从其中抽取 |
| `cooldown_seconds` | `10` | 每个群独立计算的非负整数冷却秒数 |
| `message_type` | `command` | 匹配类型：`command`、`keyword` 或 `regex` |
| `message` | `随机<资源池ID>` | 触发条件列表；正则模式必须为 `[表达式, 展示文本]` |
| `insert_message` | 根据 `message` 生成 | 图片资源池的添加命令列表 |
| `delete_message` | 根据 `message` 生成 | 图片资源池的删除命令列表 |
| `modify_admin_only` | `true` | 是否只允许群主、群管理员和超级管理员增删图片 |
| `is_tome` | `false` | 触发抽取时是否必须 @机器人 |
| `output_prefix` | 空字符串 | 文本或图片输出前缀 |
| `output_suffix` | 空字符串 | 文本或图片输出后缀 |
| `is_at_sender` | `false` | 发送文本或图片时是否 @触发者 |

`output_prefix` 和 `output_suffix` 支持以下占位符：

| 占位符 | 内容 |
|---|---|
| `{filename}` | 素材文件名，包含扩展名 |
| `{filestem}` | 素材文件名，不包含扩展名 |

资源池 ID 来自目录名，只允许小写字母、数字、下划线和连字符，长度为 1～32 个字符，并且必须以字母或数字开头。

## 📦 支持的素材

| 输出类型 | 文件扩展名 |
|---|---|
| `text` | `.txt`，按 UTF-8 读取 |
| `image` | `.gif`、`.png`、`.jpg`、`.jpeg`、`.webp` |
| `record` | `.mp3`、`.wav`、`.ogg`、`.flac` |
| `video` | `.mp4`、`.avi`、`.flv`、`.wmv`、`.mov`、`.mpg`、`.mpeg` |

命令模式下可以在抽取命令后附加文件名前缀，插件会从文件名以该前缀开头的候选素材中随机选择。

图片资源池支持在群聊中发送或回复图片进行添加、删除。添加时会验证图片内容，只接受 PNG、JPEG、GIF 和 WebP；删除会移除内容哈希相同的所有图片。

## 🎛️ 管理命令

### 查看与群内开关

| 命令 | 权限 | 说明 |
|---|---|---|
| `随机池列表` | 群成员 | 查看当前群可见的资源池截图面板 |
| `开启随机池 <资源池ID...>` | 群主、群管理员或超级管理员 | 在当前群显式开启资源池，可覆盖全局禁用 |
| `关闭随机池 <资源池ID...>` | 群主、群管理员或超级管理员 | 在当前群显式关闭资源池 |

### 跨群与全局管理

| 命令 | 权限 | 说明 |
|---|---|---|
| `随机池列表 <群号>` | 超级管理员 | 查看指定群的完整资源池状态 |
| `开启群随机池 <群号> <资源池ID...>` | 超级管理员 | 为指定群开启资源池 |
| `关闭群随机池 <群号> <资源池ID...>` | 超级管理员 | 为指定群关闭资源池 |
| `全局启用随机池 <资源池ID...>` | 超级管理员 | 恢复资源池的全局默认开启状态 |
| `全局禁用随机池 <资源池ID...>` | 超级管理员 | 默认对所有群禁用资源池；群显式开启仍可覆盖 |

群级和全局开关保存在 `data/random/group_switches.json`，写入过程使用临时文件替换，避免部分写入。

### 动态资源池管理

| 命令 | 权限 | 说明 |
|---|---|---|
| `新增随机池` | 超级管理员 | 通过交互式会话创建配置并立即注册 Matcher |
| `编辑随机池 <资源池ID>` | 超级管理员 | 修改配置并立即重建 Matcher |
| `删除随机池 <资源池ID>` | 超级管理员 | 确认后归档资源池并注销 Matcher |
| `随机池归档列表` | 超级管理员 | 查看可恢复的归档 ID |
| `恢复随机池 <归档ID>` | 超级管理员 | 恢复资源池并立即注册 Matcher |

删除操作不会直接销毁素材，而是将整个资源池移动到 `data/random_archive/<时间戳>--<资源池ID>`。

## 🔐 权限与状态优先级

资源池状态按以下顺序解析：

1. 群显式开启；
2. 群显式关闭；
3. 全局默认禁用；
4. 默认开启。

群级冷却按“群号 + 资源池 ID”分别计算，不同群互不影响。抽取发送失败时会释放本次冷却占用。

## 📝 更新日志

### 0.1.0

- 重构为动态资源池注册与管理架构。
- 新增网页截图管理面板及文本降级响应。
- 新增群级开关、全局默认状态和超级管理员跨群管理。
- 新增群级冷却、文本抽取、直接/分层抽取模式。
- 新增运行时创建、编辑、归档与恢复资源池。
- 使用 Pydantic v2 严格校验配置，并增强图片内容与文件名安全校验。
- 将图片增删权限默认值调整为仅管理员。

<details>
<summary>历史版本（展开/收起）</summary>

### 0.0.9

- 添加删除图片默认所有人可以添加，要仅管理员需要单独设置
- 支持视频抽取

### 0.0.8

- 支持动态删除图片（仅command）

### 0.0.7

- 规定读取config.json文件必须为UTF-8编码
- 输出前后缀支持文件名
- 添加图片仅管理员可以操作

### 0.0.6

- 支持动态添加图片（仅command）

### 0.0.5

- 支持根据文件名定向抽取文件（仅command）

### 0.0.4

- 去除draw_mode，现在可以抽取该文件夹下符合格式的全部文件
- 代码优化，分离config

### 0.0.3

- 支持正则命令匹配

### 0.0.2

- 修复未配置"message"时不能正常使用随机命令的bug
- 支持输出前后缀配置和at发送者

### 0.0.1

- 插件初次发布

</details>

## 💡 特别感谢

- [noneplugin/nonebot-plugin-petpet](https://github.com/noneplugin/nonebot-plugin-petpet) Nonebot2 插件，用于制作摸头等头像相关表情包

## 📄 开源许可

本项目使用 [MIT License](./LICENSE) 开源。
