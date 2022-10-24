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
<img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">

</div>

## 📖 介绍

如果只是想简单做个抽图或者抽语音的功能，不需要自己写多余的代码

只需要安装本插件，在对应路径放好相关资源并配置好即可

## 💿 安装
插件仍在开发中，遇到问题还请务必提 issue。

<details>
<summary>使用 nb-cli 安装</summary>
在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装

    nb plugin install nonebot-plugin-random

</details>

<details>
<summary>使用包管理器安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 根据你使用的包管理器, 输入相应的安装命令

<details>
<summary>pip</summary>

    pip install nonebot-plugin-random
</details>
<details>
<summary>pdm</summary>

    pdm add nonebot-plugin-random
</details>
<details>
<summary>poetry</summary>

    poetry add nonebot-plugin-random
</details>
<details>
<summary>conda</summary>

    conda install nonebot-plugin-random
</details>

打开 nonebot2 项目的 `bot.py` 文件, 在其中写入

    nonebot.load_plugin('nonebot_plugin_random')

</details>

<details>
<summary>从 github 安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 输入以下命令克隆此储存库

    git clone https://github.com/jcjrobert/nonebot-plugin-random.git

打开 nonebot2 项目的 `bot.py` 文件, 在其中写入

    nonebot.load_plugin('src.plugins.nonebot_plugin_random')

</details>

## 🎉 使用

机器人每次在重启时会创建（如果没有）并读取机器人运行目录下的 `data/random/` 文件夹

然后依次读取每个文件夹，一个文件夹就是一个抽取功能

以随机capoo为例，你可以在 `data/random` 下创建capoo文件夹，然后把你喜欢的capoo图片放入文件夹

之后重启，使用命令 `随机capoo` 即可

### ⚙️ 配置

如果你有自定义命令的需求，你可以在当前文件夹，以随机capoo为例

即`data/random/capoo`下添加config.json文件，然后按照下表进行配置并重启

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| "draw_output" | 否 | "image" | 抽取输出类型，有"image"/"record" |
| "draw_mode" | 否 | "direct" | 抽取方式，"direct"表示直接从当前文件夹抽取，"indirect"表示随机从当前文件夹抽取一个文件夹然后从该文件夹抽取 |
| "message_type" | 否 | "command" | 命令响应类型，"command"即on_command，"keyword"即on_keyword |
| "message" | 否 | ["随机`当前文件夹文件名`"] | 自定义命令，必须是列表，若"message_type"不为"command"则只取第一项 |
| "is_tome" | 否 | false | 使用抽取命令时是否需要at机器人 |

## 📝 TODO LIST

- 支持正则（主要是不知道怎么整合到命令里）
- 对随机命令进行开关管理
- 支持文本抽取
- 菜单生成

## 📝 更新日志

### 0.0.1

- 插件初次发布

## 💡 特别感谢

- [noneplugin/nonebot-plugin-petpet](https://github.com/noneplugin/nonebot-plugin-petpet) Nonebot2 插件，用于制作摸头等头像相关表情包

## 其他

capoo资源请自行网上查找（（（