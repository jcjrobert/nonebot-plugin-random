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
<a href="https://jq.qq.com/?_wv=1027&k=x4krZXBW">
    <img src="https://img.shields.io/badge/QQ%E7%BE%A4-816538892-orange" alt="qq group">
</a>

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

    nonebot.load_plugin('nonebot-plugin-random')

</details>

<details>
<summary>从 github 安装</summary>
在 nonebot2 项目的插件目录下, 打开命令行, 输入以下命令克隆此储存库

    git clone https://github.com/jcjrobert/nonebot-plugin-random.git

打开 nonebot2 项目的 `bot.py` 文件, 在其中写入

    nonebot.load_plugin('src.plugins.nonebot-plugin-random')

</details>

## 🎉 使用

机器人每次在重启时会创建（如果没有）并读取机器人运行目录下的 `data/random/` 文件夹

然后依次读取每个文件夹，一个文件夹就是一个抽取功能

以随机capoo为例，你可以在 `data/random` 下创建capoo文件夹，然后把你喜欢的capoo图片放入文件夹

之后重启，使用命令 `随机capoo` 即可

可以在群里动态添加图片，使用命令 `添加随机capoo` + 图片 + 图片名（可选） 即可，可以回复添加，仅管理员可以添加

删除图片则使用命令`删除随机capoo` + 图片即可，可以回复删除，仅管理员可以删除，会删除全部拥有同样hash的图片

目前不能动态添加文件夹，需要手动添加并重启，这点请注意

### ⚙️ 配置

如果你有自定义命令的需求，你可以在当前文件夹，以随机capoo为例

即`data/random/capoo`下添加config.json（UTF-8编码）文件，然后按照下表进行配置并重启

| 配置项 | 必填 | 默认值 | 说明 |
|:-----:|:----:|:----:|:----:|
| "draw_output" | 否 | "image" | 抽取输出类型，有"image"/"record"/"video" |
| "message_type" | 否 | "command" | 命令响应类型，"command"即on_command，"keyword"即on_keyword, "regex"即on_regex |
| "message" | 否 | ["随机`当前文件夹文件名`"] | 自定义命令，必须是列表，若"message_type"为"keyword"时只取第一项，为"regex"时必须为两项，第一项是正则表达式，第二项是匹配表达式的命令 |
| "insert_message" | 否 | ["添加随机`当前文件夹文件名`"] | 自定义添加图片命令，必须是列表，仅"message_type"为"command"且"message_type"为"image"时有效 |
| "delete_message" | 否 | ["删除随机`当前文件夹文件名`"] | 自定义删除图片命令，同上 |
| "modify_admin_only" | 否 | false | 添加删除图片是否仅管理员可操作 |
| "is_tome" | 否 | false | 使用抽取命令时是否需要at机器人 |
| "output_prefix" | 否 | "" | 输出前缀，"draw_output"仅为"image"时有效，下同 |
| "output_suffix" | 否 | "" | 输出后缀 |
| "is_at_sender" | 否 | false | 机器人发消息时是否需要at发送者 |

如果想在输出前后缀出现文件名，请用{filestem}代表文件名，{filename}代表带后缀的文件名

### 指令表

| 指令 | 说明 |
|:-----:|:----:|
| 随机XX | 指令可见上述配置|
| 随机XX + 文件名 | 仅在"message_type"为"command"时生效，指定文件名字（搜索第一个开头为指定名称的文件，可包括后缀） |
| 添加随机XX + 图片名 | 仅在"message_type"为"command"且"message_type"为"image"时生效，添加指令可自定义，可添加数张图片，空格隔开可以分别对图片命名，可以回复添加，图片名默认为当前时间的时间戳+自动判断图片的后缀 |
| 删除随机XX | 仅在"message_type"为"command"且"message_type"为"image"时生效，删除指令可自定义，可删除数张图片，可以回复删除 |

目前去除command前缀的手段非常暴力，直接遍历command并依次进行replace，进行自定义命令时需额外注意这点，如果有完美的解决方案欢迎提出issue或PR

### 支持的文件后缀

| draw_output | suffix |
|:-----:|:----:|
| image | gif,png,jpg,jpeg |
| record | mp3,wav,ogg |
| video | mp4,avi,flv,wmv,mov,mpg,mpeg |

仅在上表的文件后缀才会被纳入随机抽取的列表当中，时间原因，只确认了这些后缀，如果有其他可以用的后缀欢迎提出issue或PR

## 📝 TODO LIST

- [ ] 对随机命令进行开关管理
- [ ] 支持文本抽取
- [ ] 菜单生成
- [ ] 支持文件统计
- [ ] 支持设置额外的文件路径进行文件抽取

## 📝 更新日志

<details>
<summary>展开/收起</summary>

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

## 其他

capoo资源欢迎加入交流群获取，日后可能会开放远程下载

## 📄 开源许可

本项目使用[MIT](./LICENSE)许可证开源

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.