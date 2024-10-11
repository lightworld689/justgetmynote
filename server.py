from flask import Flask, request, jsonify, send_from_directory, Response
import sqlite3
import re
import os
import logging
from functools import wraps
from datetime import datetime
import secrets  # For generating secure random share IDs

app = Flask(__name__)

# 配置
DATABASE = 'content.db'
MAIN_TEXT_FILE = 'main.txt'
PORT = 6094
META_FOLDER = 'meta'
LOG_FILE = 'log.log'
FAVICON_FILE = 'favicon.ico'

# 正则表达式用于验证标识符（3-24 个字母或数字）
ID_REGEX = re.compile(r'^[A-Za-z0-9]{3,24}$')
SHARE_ID_REGEX = re.compile(r'^[A-Fa-f0-9]{16}$')  # 16-character hex

# 禁用 Flask 默认的日志
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True

# 设置自定义日志
logger = logging.getLogger('custom_logger')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 初始化数据库
def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS contents (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL
            )
        ''')
        # 插入一些初始数据（可根据需要修改）
        initial_data = [
            ('dqjl', 'hi y'),
        ]
        c.executemany('INSERT OR IGNORE INTO contents (id, content) VALUES (?, ?)', initial_data)
        conn.commit()
        conn.close()
        print("数据库已初始化。")
    else:
        print("数据库已存在。")

# 初始化 main.txt
def init_main_txt():
    if not os.path.exists(MAIN_TEXT_FILE):
        with open(MAIN_TEXT_FILE, 'w', encoding='utf-8') as f:
            f.write("这是 main.txt 的内容。")
        print("main.txt 已创建。")
    else:
        print("main.txt 已存在。")

# 确保 meta 文件夹和 bg.png 存在
def init_meta():
    if not os.path.exists(META_FOLDER):
        os.makedirs(META_FOLDER)
        print(f"{META_FOLDER} 文件夹已创建。")
    # 检查 bg.png 是否存在，如果不存在，可以创建一个占位图片或提示用户添加
    bg_path = os.path.join(META_FOLDER, 'bg.png')
    if not os.path.exists(bg_path):
        try:
            from PIL import Image
            img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            img.save(bg_path)
            print(f"{bg_path} 已创建。请替换为您需要的背景图片。")
        except ImportError:
            print("Pillow 未安装，无法创建占位图片。请手动添加 meta/bg.png。")

# 初始化 favicon.ico
def init_favicon():
    if not os.path.exists(FAVICON_FILE):
        try:
            from PIL import Image
            img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            img.save(FAVICON_FILE)
            print(f"{FAVICON_FILE} 已创建。请替换为您需要的 favicon.ico。")
        except ImportError:
            print("Pillow 未安装，无法创建占位 favicon.ico。请手动添加 favicon.ico。")

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# 获取内容
def get_content(identifier):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT content FROM contents WHERE id = ?', (identifier,))
    row = c.fetchone()
    conn.close()
    if row:
        return row['content']
    else:
        return ""  # 返回空字符串而不是提示

# 更新或插入内容
def upsert_content(identifier, new_content):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO contents (id, content) VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET content=excluded.content
    ''', (identifier, new_content))
    conn.commit()
    conn.close()

# 生成唯一的16字符十六进制共享ID
def generate_share_id():
    while True:
        share_id = secrets.token_hex(8)  # 16 characters
        if not get_content(share_id):
            return share_id

# 日志记录装饰器
def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = f(*args, **kwargs)
        ip = request.remote_addr
        path = request.path
        method = request.method
        log_entry = f"{ip} - {path} - {method}"
        logger.info(log_entry)
        return response
    return decorated_function

# 主路由，处理 /0, /1, /main, /index, /share/<share_id>, /<id>, /
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@log_request
def serve_content(path):
    # 处理主路由
    if path in ['', '0', '1', 'main', 'index']:
        try:
            with open(MAIN_TEXT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            content = ""
        display_path = '/' if path == '' else f'/{path}'
        return render_html(content, read_only=True, path=display_path)
    
    # 处理 /share/<share_id> 路由
    if path.startswith('share/'):
        share_id = path.split('share/')[1]
        if not SHARE_ID_REGEX.fullmatch(share_id):
            return "Invalid Share ID", 400
        content = get_content(share_id)
        if not content:
            return "Share ID not found", 404
        flag = f'''
            <a href="https://github.com/lightworld689/justgetmytext" target="_blank">JustGetMyText</a> - Shared with you - ReadOnly
        '''
        return render_html(content, read_only=True, path=f'/share/{share_id}', custom_flag=flag)
    
    # 处理 /<id> 路由
    if ID_REGEX.fullmatch(path):
        identifier = path
        content = get_content(identifier)
        display_path = f'/{identifier}'
        return render_html(content, read_only=False, path=display_path, identifier=identifier)
    
    # 如果路由不匹配，返回 404
    return "404 Not Found", 404

# 更新内容的API
@app.route('/update/<identifier>', methods=['POST'])
@log_request
def update(identifier):
    # 验证标识符
    if not ID_REGEX.fullmatch(identifier):
        return jsonify({'status': 'error', 'message': '无效的标识符。'}), 400
    
    # 获取新内容
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'status': 'error', 'message': '缺少内容。'}), 400
    
    new_content = data['content']
    
    # 检查内容长度
    if len(new_content) > 100000:
        return jsonify({'status': 'error', 'message': '内容长度超过100,000字符限制。'}), 400
    
    upsert_content(identifier, new_content)
    return jsonify({'status': 'success', 'message': '内容已更新。'})

# 创建共享链接的API
@app.route('/create_share/<identifier>', methods=['POST'])
@log_request
def create_share(identifier):
    # 验证标识符
    if not ID_REGEX.fullmatch(identifier):
        return jsonify({'status': 'error', 'message': '无效的标识符。'}), 400
    
    content = get_content(identifier)
    if not content:
        return jsonify({'status': 'error', 'message': '标识符不存在。'}), 404
    
    # 生成唯一的共享ID
    share_id = generate_share_id()
    
    # 插入共享内容
    upsert_content(share_id, content)
    
    share_url = f"/share/{share_id}"
    return jsonify({'status': 'success', 'share_url': share_url})

# 提供静态文件（如 /meta/bg.png）
@app.route('/meta/<path:filename>')
@log_request
def meta_static(filename):
    return send_from_directory(META_FOLDER, filename)

# 提供 favicon.ico
@app.route('/favicon.ico')
@log_request
def favicon():
    if os.path.exists(FAVICON_FILE):
        return send_from_directory('.', FAVICON_FILE)
    else:
        return "", 204  # No Content

# 渲染HTML页面
def render_html(content, read_only=False, path='/', identifier=None, custom_flag=None):
    # 内联CSS
    css = """
    <style>
    @media screen {
      body {
        background:url(/meta/bg.png) top left repeat #ebeef2;
        font-family:Helvetica,Tahoma,Arial,STXihei,华文细黑,microsoft yahei,微软雅黑,SimSun,宋体,Heiti,黑体,sans-serif;
        font-size:15px
      }
      .stack {
        position:fixed;
        left:1em;
        top:1em;
        right:1em;
        bottom:1.8em
      }
      .layer {
        position:absolute;
        left:-3px;
        right:-3px;
        top:-3px;
        bottom:1px;
        background-color:#fff;
        border-radius:3.456789px;
        border:1px solid #ddd;
        box-shadow:0 0 5px 0 #e4e4e4
      }
      .flag {
        position:fixed;
        left:0;
        right:0;
        bottom:1em;
        height:.8em;
        text-align:center;
        color:#aaa;
        font-size:14px
      }
      a:link,
      a:visited,
      a:active {
        color:#aaa;
        text-decoration:none;
        word-break:break-all;
        -webkit-tap-highlight-color:transparent
      }
      *:focus {
        outline:none
      }
      .content {
        width:100%;
        height:100%;
        min-height:100%;
        resize:none;
        overflow-y:auto;
        border-radius:3px;
        box-sizing:border-box;
        border:none;
        padding:.7em .8em;
        color:#333;
        font-size:1.1em
      }
      .print {
        display:none
      }
    }
    @media print {
      .container,
      .stack,
      .layer,
      .flag {
        display:none
      }
      a:link,
      a:visited,
      a:active {
        color:#aaa;
        text-decoration:none;
        word-break:break-all;
        -webkit-tap-highlight-color:transparent
      }
      .print {
        font-size:1.1em
      }
    }
    html {
      line-height:1.15;
      -ms-text-size-adjust:100%;
      -webkit-text-size-adjust:100%
    }
    body {
      margin:0
    }
    article,
    aside,
    footer,
    header,
    nav,
    section {
      display:block
    }
    h1 {
      font-size:2em;
      margin:.67em 0
    }
    figcaption,
    figure,
    main {
      display:block
    }
    figure {
      margin:1em 40px
    }
    hr {
      box-sizing:content-box;
      height:0;
      overflow:visible
    }
    pre {
      font-size:1em
    }
    a {
      background-color:transparent;
      -webkit-text-decoration-skip:objects
    }
    a:active,
    a:hover {
      outline-width:0
    }
    abbr[title] {
      border-bottom:none;
      text-decoration:underline;
      text-decoration:underline dotted
    }
    b,
    strong {
      font-weight:inherit
    }
    b,
    strong {
      font-weight:bolder
    }
    code,
    kbd,
    samp {
      font-size:1em
    }
    dfn {
      font-style:italic
    }
    mark {
      background-color:#ff0;
      color:#000
    }
    small {
      font-size:80%
    }
    sub,
    sup {
      font-size:75%;
      line-height:0;
      position:relative;
      vertical-align:baseline
    }
    sub {
      bottom:-.25em
    }
    sup {
      top:-.5em
    }
    audio,
    video {
      display:inline-block
    }
    audio:not([controls]) {
      display:none;
      height:0
    }
    img {
      border-style:none
    }
    svg:not(:root) {
      overflow:hidden
    }
    button,
    input,
    optgroup,
    select,
    textarea {
      font-family:Helvetica,Tahoma,Arial,STXihei,华文细黑,microsoft yahei,微软雅黑,SimSun,宋体,Heiti,黑体,sans-serif;
      font-size:15px;
      line-height:1.15;
      margin:0
    }
    button,
    input {
      overflow:visible
    }
    button,
    select {
      text-transform:none
    }
    button,
    html [type=button],
    [type=reset],
    [type=submit] {
      -webkit-appearance:button
    }
    button::-moz-focus-inner,
    [type=button]::-moz-focus-inner,
    [type=reset]::-moz-focus-inner,
    [type=submit]::-moz-focus-inner {
      border-style:none;
      padding:0
    }
    button:-moz-focusring,
    [type=button]:-moz-focusring,
    [type=reset]:-moz-focusring,
    [type=submit]:-moz-focusring {
      outline:1px dotted ButtonText
    }
    fieldset {
      border:1px solid silver;
      margin:0 2px;
      padding:.35em .625em .75em
    }
    legend {
      box-sizing:border-box;
      color:inherit;
      display:table;
      max-width:100%;
      padding:0;
      white-space:normal
    }
    progress {
      display:inline-block;
      vertical-align:baseline
    }
    textarea {
      overflow:auto
    }
    [type=checkbox],
    [type=radio] {
      box-sizing:border-box;
      padding:0
    }
    [type=number]::-webkit-inner-spin-button,
    [type=number]::-webkit-outer-spin-button {
      height:auto
    }
    [type=search] {
      -webkit-appearance:textfield;
      outline-offset:-2px
    }
    [type=search]::-webkit-search-cancel-button,
    [type=search]::-webkit-search-decoration {
      -webkit-appearance:none
    }
    ::-webkit-file-upload-button {
      -webkit-appearance:button;
      font:inherit
    }
    details,
    menu {
      display:block
    }
    summary {
      display:list-item
    }
    canvas {
      display:inline-block
    }
    template {
      display:none
    }
    [hidden] {
      display:none
    }
    </style>
    """
    
    # 内联JavaScript，实现客户端每秒检测内容变化，并处理分享按钮
    if not read_only:
        js = f"""
        <script>
        (function(){{
            document.addEventListener('DOMContentLoaded', function() {{
                const contentArea = document.getElementById('content');
                let lastContent = contentArea.value;

                // 自动保存内容 every second
                setInterval(function() {{
                    const currentContent = contentArea.value;
                    if (currentContent !== lastContent) {{
                        fetch('/update/{identifier}', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{ 'content': currentContent }})
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                console.log('更新成功');
                                lastContent = currentContent;
                            }} else {{
                                alert(data.message);
                            }}
                        }})
                        .catch((error) => {{
                            console.error('Error:', error);
                        }});
                    }}
                }}, 1000); // 每秒检测一次

                // 处理Share按钮点击
                const shareButton = document.getElementById('shareButton');
                if (shareButton) {{
                    shareButton.addEventListener('click', function() {{
                        fetch('/create_share/{identifier}', {{
                            method: 'POST'
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                const shareUrl = window.location.origin + data.share_url;
                                window.open(shareUrl, '_blank');
                            }} else {{
                                alert(data.message);
                            }}
                        }})
                        .catch((error) => {{
                            console.error('Error:', error);
                        }});
                    }});
                }}
            }});
        }})();
        </script>
        """
    else:
        js = ""  # No JavaScript needed for read-only pages

    # 构建 flag 部分
    if custom_flag:
        flag = custom_flag
    else:
        flag = f'''
        <a href="https://github.com/lightworld689/justgetmytext" target="_blank">JustGetMyText</a> - {path}
        '''
        if read_only:
            flag += " - ReadOnly"

    # 构建HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>JustGetMyText</title>
        {css}
    </head>
    <body>
        <div class="stack">
            <div class="layer">
                <textarea id="content" class="content" {'readonly' if read_only else ''} maxlength="100000" style="height:90%; width:100%;">{content}</textarea>
                {'<button id="shareButton" style="margin-top:10px;">Share</button>' if not read_only else ''}
            </div>
        </div>
        <div class="flag">
            {flag}
        </div>
        {'' if read_only else js}
    </body>
    </html>
    """
    return Response(html, mimetype='text/html')

# 启动服务器
if __name__ == '__main__':
    # 初始化数据库和文件
    init_db()
    init_main_txt()
    init_meta()
    init_favicon()

    # 启动 Flask 服务器
    app.run(host='0.0.0.0', port=PORT, threaded=True)
