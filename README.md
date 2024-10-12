# JustGetMyNote 服务器

**JustGetMyNote** 是一个基于 Flask 框架的简易服务器，用于管理和展示文本内容。它支持从 SQLite 数据库或 `main.txt` 文件中获取内容，并提供一个前端界面供用户查看和编辑内容。所有请求都会被记录到日志文件中，便于追踪和管理。此外，服务器还支持生成共享链接以及维护模式，确保在需要时能够限制内容的修改和访问。css以及部分功能借鉴[note.ms](https://note.ms)。

**现在可以与他人共享只读笔记了！**

## 目录

- [功能](#功能)
- [项目结构](#项目结构)
- [前提条件](#前提条件)
- [安装](#安装)
- [运行服务器](#运行服务器)
- [访问内容](#访问内容)
  - [只读内容](#只读内容)
  - [可编辑内容](#可编辑内容)
  - [共享链接](#共享链接)
- [编辑与更新](#编辑与更新)
- [日志记录](#日志记录)
- [静态文件](#静态文件)
  - [背景图片](#背景图片)
  - [网站图标](#网站图标)
- [维护模式](#维护模式)
- [自定义与扩展](#自定义与扩展)
- [注意事项](#注意事项)
- [许可证](#许可证)

## 功能

- **内容管理**：
  - 根据不同的 URL 路径，从 SQLite 数据库或 `main.txt` 文件中获取内容。
  - 支持查看和编辑内容。
  - 如果内容标识符不存在，自动创建新的数据库记录。
  - 通过共享链接 (`/share/<share_id>`) 以只读模式共享内容。

- **前端交互**：
  - 借鉴[note.ms](https://note.ms)的css。
  - 通过 JavaScript 每秒检测内容变化，并在变化时自动发送更新请求，实现自动保存功能。
  - 支持“分享”按钮，生成共享链接以只读模式展示内容。
  - 只读模式与可编辑模式下显示不同的信息。

- **日志记录**：
  - 记录每个请求的 IP、请求地址和请求方法到 `log.log` 文件中，格式为 `IP - 请求地址 - POST/GET`。

- **初始化**：
  - 自动初始化 SQLite 数据库、`main.txt` 文件、背景图片 `meta/bg.png` 和图标 `favicon.ico`（如果不存在）。
  - 支持维护模式，通过 `settings/main.txt` 配置文件启用。

- **缓存机制**：
  - 定时（每10秒）从文件系统中读取 `main.txt` 和 `settings/main.txt`，更新内存缓存，提高访问效率。

## 项目结构

```
JustGetMyNote/
│
├── server.py                # 服务器端代码
├── main.txt                 # 主文本文件（自动创建）
├── content.db               # SQLite 数据库文件（自动创建）
├── log.log                  # 日志文件（自动创建）
├── favicon.ico              # 网站图标（自动创建，占位符）
├── meta/
│   └── bg.png               # 背景图片（自动创建，占位符）
├── settings/
│   └── main.txt             # 设置文件（用于配置维护模式）
└── requirements.txt         # Python 依赖包列表
```

## 前提条件

- **Python 3.6+**：确保已安装 Python。
- **依赖库**：
  - `Flask`：用于构建服务器。
  - `Pillow`：用于创建占位图片和图标。

## 安装

1. **克隆仓库**：

   ```bash
   git clone https://github.com/lightworld689/JustGetMyNote.git
   cd JustGetMyNote
   ```

2. **创建并激活虚拟环境（可选，但推荐）**：

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # 对于 Windows 用户：venv\Scripts\activate
   ```

3. **安装依赖库**：

   ```bash
   pip install -r requirements.txt
   ```

   **`requirements.txt` 内容示例**：

   ```plaintext
   Flask
   Pillow
   ```

## 运行服务器

在项目根目录下，运行以下命令启动服务器：

```bash
python server.py
```

服务器将监听 `0.0.0.0:6094`。首次运行时，脚本将自动初始化数据库和必要的文件（如果它们不存在）。

**输出示例**：

```
数据库已初始化。
main.txt 已创建。
meta 文件夹已创建。
meta/bg.png 已创建。请替换为您需要的背景图片。
favicon.ico 已创建。请替换为您需要的 favicon.ico。
settings 文件夹已创建。
settings/main.txt 已创建。
 * Serving Flask app 'server'
 * Running on http://0.0.0.0:6094/ (Press CTRL+C to quit)
```

## 访问内容

### 只读内容

访问以下路径将显示 `main.txt` 的内容，并以只读模式展示：

- [http://localhost:6094/](http://localhost:6094/)
- [http://localhost:6094/0](http://localhost:6094/0)
- [http://localhost:6094/1](http://localhost:6094/1)
- [http://localhost:6094/main](http://localhost:6094/main)
- [http://localhost:6094/index](http://localhost:6094/index)

下方将显示：

```
JustGetMyNote - /path - ReadOnly
```

### 可编辑内容

访问以下路径将从 SQLite 数据库中获取对应标识符的内容，并以可编辑模式展示：

- [http://localhost:6094/abcd](http://localhost:6094/abcd)
- [http://localhost:6094/efgh](http://localhost:6094/efgh)

下方将显示：

```
JustGetMyNote - /abcd
```

如果标识符不存在，页面将显示空白，允许通过编辑框创建新内容。

### 共享链接

生成共享链接后，可以通过以下路径以只读模式访问内容：

- [http://localhost:6094/share/<share_id>](http://localhost:6094/share/<share_id>)

共享链接示例：

```
JustGetMyNote - Shared with you - ReadOnly
```

## 编辑与更新

在可编辑页面中修改内容后，客户端的 JavaScript 将每秒检测一次内容变化：

- 如果检测到内容变化，自动发送 `POST` 请求到 `/update/<id>` 路径。
- 服务器接收到请求后，将更新或插入对应的内容到 SQLite 数据库中。
- 更新成功后，控制台将显示“更新成功”，并更新 `lastContent` 以避免重复提交。

**更新请求示例**：

```json
{
  "status": "success"
}
```

如果更新失败，会返回相应的错误信息。

## 日志记录

所有的访问日志将记录在 `log.log` 文件中，格式如下：

```
127.0.0.1 - /abcd - GET
127.0.0.1 - /abcd - POST
```

每条日志包含：

- **IP 地址**：发起请求的客户端 IP。
- **请求路径**：访问的 URL 路径。
- **请求方法**：`GET` 或 `POST`。

## 静态文件

### 背景图片

默认背景图片存储在 `meta/bg.png`。首次运行时，脚本将创建一个 1x1 像素透明 PNG 作为占位符。请替换为您需要的背景图片。

访问 [http://localhost:6094/meta/bg.png](http://localhost:6094/meta/bg.png) 可以查看背景图片。

### 网站图标

`favicon.ico` 存储在项目根目录。首次运行时，脚本将创建一个 16x16 像素透明 PNG 作为占位符。请替换为您需要的图标。

访问 [http://localhost:6094/favicon.ico](http://localhost:6094/favicon.ico) 将显示网站图标。

## 维护模式

通过编辑 `settings/main.txt` 文件，可以启用或禁用维护模式（Construction Mode）。

**启用维护模式**：

在 `settings/main.txt` 中设置 `construction = true`：

```ini
# Change this to enter read-only mode and the user will not be able to modify anything.
construction = true
```

启用后，所有可编辑页面将以只读模式展示，且不允许创建共享链接或修改内容。

**禁用维护模式**：

将 `construction` 设置为 `false`：

```ini
# Change this to enter read-only mode and the user will not be able to modify anything.
construction = false
```

更改后，服务器会在下一次缓存更新时应用新的设置。

## 自定义与扩展

- **添加新内容**：
  - 通过访问一个新的标识符路径（例如 `/ijkl`），并在可编辑页面中输入内容，服务器将自动创建新的数据库记录。

- **生成共享链接**：
  - 在可编辑页面中点击“Share”按钮，生成一个共享链接，以只读模式展示内容。

- **更改端口**：
  - 在 `server.py` 中修改 `PORT` 变量以更改服务器监听的端口。

- **更换背景图片和图标**：
  - 替换 `meta/bg.png` 和项目根目录下的 `favicon.ico` 为您需要的图片和图标。

- **扩展内容字段**：
  - 可以在 `contents` 表中添加更多字段，如标题、时间戳等，以扩展功能。

## 注意事项

- **安全性**：
  - 当前示例未实现身份验证或权限控制。在生产环境中，请确保添加必要的安全措施，如身份验证、权限管理等，以防止未经授权的访问和修改。

- **错误处理**：
  - 目前的错误处理较为基础。根据需要，可以增强错误处理和用户反馈，确保在各种异常情况下用户能够得到明确的提示。

- **依赖库**：
  
    ```bash
    pip install -r requirements.txt
    ```

- **并发访问**：
  - 服务器使用多线程模式 (`threaded=True`) 以支持并发访问。但对于高负载应用，建议使用更强大的 WSGI 服务器如 Gunicorn。

- **数据备份**：
  - 定期备份 `content.db` 和相关文件，以防止数据丢失。

## 许可证

本项目使用 [AGPL 3.0 许可证](LICENSE)。

---

**感谢使用 JustGetMyNote！**

如有任何问题或建议，欢迎提交 [issue](https://github.com/lightworld689/JustGetMyNote/issues) 或联系作者。
