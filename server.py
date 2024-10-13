from flask import Flask, request, jsonify, send_from_directory, Response
import sqlite3
import re
import os
import logging
from functools import wraps
import secrets  # For generating secure random share IDs
import html     # Import html module for escaping
import threading
import time
import queue  # Import queue module for write tasks

app = Flask(__name__)

# 配置
DATABASE = 'content.db'
MAIN_TEXT_FILE = 'main.txt'
PORT = 6094
META_FOLDER = 'meta'
LOG_FILE = 'log.log'
FAVICON_FILE = 'favicon.ico'
SETTINGS_FOLDER = 'settings'
MAIN_SETTINGS_FILE = os.path.join(SETTINGS_FOLDER, 'main.txt')

# 正则表达式用于验证标识符（3-24 个字母或数字）
ID_REGEX = re.compile(r'^[A-Za-z0-9]{3,24}$')
SHARE_ID_REGEX = re.compile(r'^[A-Fa-f0-9]{16}$')  # 16-character hex
BURN_ID_REGEX = re.compile(r'^[A-Fa-f0-9]{16}$')   # 16-character hex for burn links

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

# 缓存结构
cache = {
    'main_text': '',
    'settings': {},
    'contents': {},        # id -> content
    'share_contents': {},  # share_id -> content
    'burn_contents': {}    # burn_id -> content
}
cache_lock = threading.Lock()

# 写入队列
write_queue = queue.Queue()

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Set row_factory to access columns by name
    c = conn.cursor()

    # 创建 contents 表，如果不存在，添加 share_id 列
    c.execute('''
        CREATE TABLE IF NOT EXISTS contents (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            share_id TEXT UNIQUE
        )
    ''')

    # 创建 burn_contents 表，如果不存在
    c.execute('''
        CREATE TABLE IF NOT EXISTS burn_contents (
            burn_id TEXT PRIMARY KEY,
            content TEXT NOT NULL
        )
    ''')

    # 插入一些初始数据（可根据需要修改）
    initial_data = [
        ('dqjl', 'hi y'),
    ]

    for identifier, content in initial_data:
        # 检查是否已经存在该标识符
        c.execute('SELECT share_id FROM contents WHERE id = ?', (identifier,))
        row = c.fetchone()
        if not row:
            # 插入初始数据，没有 share_id
            c.execute('INSERT INTO contents (id, content) VALUES (?, ?)', (identifier, content))

    conn.commit()
    conn.close()
    print("数据库已初始化。")

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

# 初始化 settings
def init_settings():
    if not os.path.exists(SETTINGS_FOLDER):
        os.makedirs(SETTINGS_FOLDER)
        print(f"{SETTINGS_FOLDER} 文件夹已创建。")
    if not os.path.exists(MAIN_SETTINGS_FILE):
        default_content = """# Change this to enter read-only mode and the user will not be able to modify anything.
construction = false
"""
        with open(MAIN_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            f.write(default_content)
        print(f"{MAIN_SETTINGS_FILE} 已创建。")
    else:
        print(f"{MAIN_SETTINGS_FILE} 已存在。")

# 读取 construction 模式（从缓存获取）
def is_construction_mode():
    with cache_lock:
        return cache['settings'].get('construction', False)

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# 获取所有内容并更新缓存
def load_all_contents_to_cache():
    conn = get_db_connection()
    c = conn.cursor()
    # 加载 contents
    c.execute('SELECT id, content, share_id FROM contents')
    rows = c.fetchall()
    # 加载 burn_contents
    c.execute('SELECT burn_id, content FROM burn_contents')
    burn_rows = c.fetchall()
    conn.close()
    contents = {}
    share_contents = {}
    for row in rows:
        contents[row['id']] = row['content']
        if row['share_id']:
            share_contents[row['share_id']] = row['content']
    burn_contents = {}
    for row in burn_rows:
        burn_contents[row['burn_id']] = row['content']
    with cache_lock:
        cache['contents'] = contents
        cache['share_contents'] = share_contents  # 更新 share_contents 缓存
        cache['burn_contents'] = burn_contents    # 更新 burn_contents 缓存

# 生成唯一的16字符十六进制共享ID
def generate_share_id():
    while True:
        share_id = secrets.token_hex(8)  # 16 characters
        if not share_id_exists(share_id):
            return share_id

# 生成唯一的16字符十六进制烧毁ID
def generate_burn_id():
    while True:
        burn_id = secrets.token_hex(8)  # 16 characters
        if not burn_id_exists(burn_id):
            return burn_id

# 检查 share_id 是否存在
def share_id_exists(share_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id FROM contents WHERE share_id = ?', (share_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

# 检查 burn_id 是否存在
def burn_id_exists(burn_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT burn_id FROM burn_contents WHERE burn_id = ?', (burn_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

# 获取内容通过 share_id（从缓存读取）
def get_content_by_share_id(share_id):
    with cache_lock:
        return cache['share_contents'].get(share_id, None)

# 获取内容通过 burn_id（从缓存读取）
def get_content_by_burn_id(burn_id):
    with cache_lock:
        return cache['burn_contents'].get(burn_id, None)

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

# 渲染HTML页面
def render_html(content, read_only=False, path='/', identifier=None, custom_flag=None, construction_mode=False, burn_after_read=False):
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
      button {
        padding: 0.5em 1em;
        font-size: 1em;
        cursor: pointer;
        margin-top: 10px;
      }
      /* 新增：保存成功提示样式 */
      .save-success {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #4CAF50; /* 绿色背景 */
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        opacity: 0;
        transition: opacity 0.5s ease-in-out;
        z-index: 1000;
      }
      /* 新增：按钮容器样式 */
      .button-container {
        display: flex;
      }
      /* 新增：弹窗样式 */
      .modal {
        display: none; 
        position: fixed; 
        z-index: 1001; 
        left: 0;
        top: 0;
        width: 100%; 
        height: 100%; 
        overflow: auto; 
        background-color: rgba(0,0,0,0.4); 
      }
      .modal-content {
        background-color: #fefefe;
        margin: 15% auto; 
        padding: 20px;
        border: 1px solid #888;
        width: 80%; 
        max-width: 500px;
        border-radius: 5px;
      }
      .close {
        color: #aaa;
        float: right;
        font-size: 28px;
        font-weight: bold;
      }
      .close:hover,
      .close:focus {
        color: black;
        text-decoration: none;
        cursor: pointer;
      }
    }
    @media print {
      .container,
      .stack,
      .layer,
      .flag,
      .button-container,
      .modal {
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
    if not read_only and identifier and not construction_mode:
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
                        fetch('/update/{html.escape(identifier)}', {{
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
                                showSaveSuccess();
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
                        fetch('/create_share/{html.escape(identifier)}', {{
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

                // 处理Share (Burn after read)按钮点击
                const burnShareButton = document.getElementById('burnShareButton');
                if (burnShareButton) {{
                    burnShareButton.addEventListener('click', function() {{
                        fetch('/create_burn/{html.escape(identifier)}', {{
                            method: 'POST'
                        }})
                        .then(response => response.json())
                        .then(data => {{
                            if (data.status === 'success') {{
                                const burnUrl = window.location.origin + data.burn_url;
                                showBurnLink(burnUrl);
                            }} else {{
                                alert(data.message);
                            }}
                        }})
                        .catch((error) => {{
                            console.error('Error:', error);
                        }});
                    }});
                }}

                // 显示保存成功的提示
                let saveSuccessTimeout = null;
                function showSaveSuccess() {{
                    const msg = document.getElementById('saveSuccess');
                    if (!msg) return;
                    msg.style.opacity = 1;
                    if (saveSuccessTimeout) {{
                        clearTimeout(saveSuccessTimeout);
                    }}
                    // 0.5秒后开始淡出
                    saveSuccessTimeout = setTimeout(() => {{
                        msg.style.opacity = 0;
                    }}, 1000); // 0.5秒淡入 + 0.5秒显示
                }}

                // 显示烧毁链接的弹窗
                function showBurnLink(url) {{
                    const modal = document.getElementById('burnModal');
                    const burnLink = document.getElementById('burnLink');
                    burnLink.href = url;
                    burnLink.textContent = url;
                    modal.style.display = 'block';
                }}

                // 处理弹窗关闭
                const closeModal = document.getElementsByClassName('close')[0];
                if (closeModal) {{
                    closeModal.onclick = function() {{
                        const modal = document.getElementById('burnModal');
                        modal.style.display = 'none';
                    }}
                }}

                // 点击弹窗外部关闭弹窗
                window.onclick = function(event) {{
                    const modal = document.getElementById('burnModal');
                    if (event.target == modal) {{
                        modal.style.display = 'none';
                    }}
                }}
            }});
        }})();
        </script>
        """
    else:
        js = ""  # No JavaScript needed for read-only pages or construction mode

    # 构建 flag 部分
    if custom_flag:
        flag = custom_flag
    else:
        # 使用html.escape确保path安全
        escaped_path = html.escape(path)
        flag = f'''
        <a href="https://github.com/lightworld689/justgetmynote" target="_blank">JustGetMyNote</a> - {escaped_path}
        '''
        if read_only:
            flag += " - ReadOnly"

    # 如果是维护模式，添加额外的信息
    if construction_mode:
        flag += " - ReadOnly is about to be restored due to construction and website may be temporarily offline"

    # 如果是阅后即焚页面，追加标识
    if burn_after_read:
        flag += " - Burn after read"

    # 如果需要，添加保存成功的提示元素
    save_success_div = '''
    <div id="saveSuccess" class="save-success">√ Saved</div>
    '''

    # 构建HTML
    # 使用html.escape(content)确保内容安全
    escaped_content = html.escape(content)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>JustGetMyNote</title>
        {css}
    </head>
    <body>
        <div class="stack">
            <div class="layer">
                <textarea id="content" class="content" {'readonly' if read_only or construction_mode or burn_after_read else ''} maxlength="100000" style="height:90%; width:100%;">{escaped_content}</textarea>
                {'''
                <div class="button-container">
                    <button id="shareButton">Share</button>
                    <button id="burnShareButton">Share (Burn after read)</button>
                </div>
                ''' if not read_only and not construction_mode and not burn_after_read else ''}
            </div>
        </div>
        <div class="flag">
            {flag}
        </div>
        {save_success_div}
        {'''
        <!-- 弹窗 -->
        <div id="burnModal" class="modal">
            <div class="modal-content">
                <span class="close">&times;</span>
                <p>Burn after read link:</p>
                <a id="burnLink" href="#" target="_blank">链接将在此显示</a>
            </div>
        </div>
        ''' if not read_only and not construction_mode and not burn_after_read else ''}
        {'' if read_only or construction_mode or burn_after_read else js}
    </body>
    </html>
    """
    return Response(html_content, mimetype='text/html')

# 主路由，处理 /0, /1, /main, /index, /share/<share_id>, /burn/<burn_id>, /<id>, /
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@log_request
def serve_content(path):
    construction_mode = is_construction_mode()

    # 处理主路由
    if path in ['', '0', '1', 'main', 'index']:
        with cache_lock:
            content = cache['main_text']
        display_path = '/' if path == '' else f'/{path}'
        # 在维护模式下，页面仍然是只读的
        return render_html(content, read_only=True, path=display_path, construction_mode=construction_mode)

    # 处理 /share/<share_id> 路由
    if path.startswith('share/'):
        share_id = path.split('share/')[1]
        if not SHARE_ID_REGEX.fullmatch(share_id):
            return "Invalid Share ID", 400
        content = get_content_by_share_id(share_id)
        if not content:
            return "Share ID not found", 404
        flag = '''
            <a href="https://github.com/lightworld689/justgetmynote" target="_blank">JustGetMyNote</a> - Shared with you - ReadOnly
        '''
        if construction_mode:
            flag += " - ReadOnly is about to be restored due to construction and website may be temporarily offline"
        return render_html(content, read_only=True, path=f'/share/{share_id}', custom_flag=flag, construction_mode=construction_mode)

    # 处理 /burn/<burn_id> 路由
    if path.startswith('burn/'):
        burn_id = path.split('burn/')[1]
        if not BURN_ID_REGEX.fullmatch(burn_id):
            return "Invalid Burn ID", 400
        content = get_content_by_burn_id(burn_id)
        if not content:
            return "Burn ID not found or already burned", 404

        # Render the content with burn_after_read flag
        response = render_html(content, read_only=True, path=f'/burn/{burn_id}', burn_after_read=True, construction_mode=construction_mode)

        # After rendering, delete the burn_id from database and cache
        def delete_burn_content(burn_id_to_delete):
            try:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute('DELETE FROM burn_contents WHERE burn_id = ?', (burn_id_to_delete,))
                conn.commit()
                conn.close()
                with cache_lock:
                    cache['burn_contents'].pop(burn_id_to_delete, None)
                logger.info(f"Burn content {burn_id_to_delete} deleted after access.")
            except Exception as e:
                logger.error(f"Error deleting burn content {burn_id_to_delete}: {e}")

        # Start a thread to delete the burn content after response is sent
        delete_thread = threading.Thread(target=delete_burn_content, args=(burn_id,), daemon=True)
        delete_thread.start()

        return response

    # 处理 /<id> 路由
    if ID_REGEX.fullmatch(path):
        identifier = path
        with cache_lock:
            content = cache['contents'].get(identifier, "")
        display_path = f'/{identifier}'
        # 如果处于维护模式，将页面设置为只读
        read_only = construction_mode
        return render_html(content, read_only=read_only, path=display_path, identifier=identifier, construction_mode=construction_mode)

    # 如果路由不匹配，返回 404
    return "404 Not Found<br />Maybe try 3-24 digit letters and numbers?", 404

# 更新内容的API
@app.route('/update/<identifier>', methods=['POST'])
@log_request
def update(identifier):
    construction_mode = is_construction_mode()
    if construction_mode:
        return jsonify({'status': 'error', 'message': 'The site is under maintenance and content cannot be modified.'}), 503

    # 验证标识符
    if not ID_REGEX.fullmatch(identifier):
        return jsonify({'status': 'error', 'message': 'Invalid identifier.'}), 400

    # 获取新内容
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'status': 'error', 'message': 'Lack of content.'}), 400

    new_content = data['content']

    # 检查内容长度
    if len(new_content) > 100000:
        return jsonify({'status': 'error', 'message': 'Content length exceeds the 100,000 character limit.'}), 400

    # 将写入任务加入队列
    write_queue.put((identifier, new_content))

    # 立即更新缓存
    with cache_lock:
        cache['contents'][identifier] = new_content
        if identifier == 'main':
            cache['main_text'] = new_content

        # 检查是否有对应的 share_id，并更新 share_contents 缓存
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT share_id FROM contents WHERE id = ?', (identifier,))
        row = c.fetchone()
        conn.close()
        if row and row['share_id']:
            share_id = row['share_id']
            cache['share_contents'][share_id] = new_content

    return jsonify({'status': 'success'})

# 创建共享链接的API
@app.route('/create_share/<identifier>', methods=['POST'])
@log_request
def create_share(identifier):
    construction_mode = is_construction_mode()
    if construction_mode:
        return jsonify({'status': 'error', 'message': 'The site is under maintenance and no shared links can be created.'}), 503

    # 验证标识符
    if not ID_REGEX.fullmatch(identifier):
        return jsonify({'status': 'error', 'message': 'Invalid identifier.'}), 400

    with cache_lock:
        content = cache['contents'].get(identifier, None)

    if content is None:
        return jsonify({'status': 'error', 'message': 'The identifier does not exist.'}), 404

    conn = get_db_connection()
    c = conn.cursor()

    # 检查是否已经存在 share_id
    c.execute('SELECT share_id FROM contents WHERE id = ?', (identifier,))
    row = c.fetchone()
    if row and row['share_id']:
        share_id = row['share_id']
    else:
        # 生成唯一的 share_id
        share_id = generate_share_id()
        try:
            c.execute('UPDATE contents SET share_id = ? WHERE id = ?', (share_id, identifier))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'status': 'error', 'message': '生成的 share_id 冲突，请重试。'}), 500

    conn.close()

    # 更新缓存中的 share_contents
    with cache_lock:
        cache['share_contents'][share_id] = content

    share_url = f"/share/{share_id}"
    return jsonify({'status': 'success', 'share_url': share_url})

# 创建阅后即焚共享链接的API
@app.route('/create_burn/<identifier>', methods=['POST'])
@log_request
def create_burn(identifier):
    construction_mode = is_construction_mode()
    if construction_mode:
        return jsonify({'status': 'error', 'message': 'The site is under maintenance and no shared links can be created.'}), 503

    # 验证标识符
    if not ID_REGEX.fullmatch(identifier):
        return jsonify({'status': 'error', 'message': 'Invalid identifier.'}), 400

    with cache_lock:
        content = cache['contents'].get(identifier, None)

    if content is None:
        return jsonify({'status': 'error', 'message': 'The identifier does not exist.'}), 404

    # 生成唯一的 burn_id
    burn_id = generate_burn_id()

    # 插入到 burn_contents 表
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO burn_contents (burn_id, content) VALUES (?, ?)', (burn_id, content))
        conn.commit()
        conn.close()
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': '生成的 burn_id 冲突，请重试。'}), 500
    except Exception as e:
        logger.error(f"Error creating burn content: {e}")
        return jsonify({'status': 'error', 'message': 'Internal server error.'}), 500

    # 更新缓存中的 burn_contents
    with cache_lock:
        cache['burn_contents'][burn_id] = content

    burn_url = f"/burn/{burn_id}"
    return jsonify({'status': 'success', 'burn_url': burn_url})

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

# 缓存更新线程函数
def update_cache():
    while True:
        try:
            # 更新 main.txt
            if os.path.exists(MAIN_TEXT_FILE):
                with open(MAIN_TEXT_FILE, 'r', encoding='utf-8') as f:
                    main_text = f.read()
                with cache_lock:
                    cache['main_text'] = main_text
            else:
                with cache_lock:
                    cache['main_text'] = ""

            # 更新 settings/main.txt
            if os.path.exists(MAIN_SETTINGS_FILE):
                with open(MAIN_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = {}
                    for line in f:
                        line = line.strip()
                        if line.startswith('#') or not line:
                            continue
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip().lower()
                            value = value.strip().lower()
                            if key == 'construction':
                                settings['construction'] = (value == 'true')
                    with cache_lock:
                        cache['settings'] = settings
            else:
                with cache_lock:
                    cache['settings'] = {}

            # 更新所有内容到缓存
            load_all_contents_to_cache()
            # 输出多了容易撑爆控制台
            # print("缓存已更新。")
        except Exception as e:
            print(f"缓存更新时出错: {e}")
        # 等待10秒
        time.sleep(10)

# 写入队列处理线程函数
def process_write_queue():
    while True:
        try:
            writes = []
            while not write_queue.empty():
                write_task = write_queue.get_nowait()
                writes.append(write_task)
            if writes:
                conn = get_db_connection()
                c = conn.cursor()
                for identifier, new_content in writes:
                    try:
                        # 尝试更新已有的内容
                        c.execute('''
                            UPDATE contents SET content = ? WHERE id = ?
                        ''', (new_content, identifier))
                        if c.rowcount == 0:
                            # 如果没有更新到任何行，说明标识符不存在，插入新的记录
                            c.execute('''
                                INSERT INTO contents (id, content) VALUES (?, ?)
                            ''', (identifier, new_content))
                    except sqlite3.IntegrityError as e:
                        logger.error(f"数据库错误: {e}")
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"处理写入队列时出错: {e}")
        # 等待10秒
        time.sleep(10)

# 启动服务器
if __name__ == '__main__':
    # 初始化数据库和文件
    init_db()
    init_main_txt()
    init_meta()
    init_favicon()
    init_settings()

    # 初次加载缓存
    try:
        # 读取 main.txt
        if os.path.exists(MAIN_TEXT_FILE):
            with open(MAIN_TEXT_FILE, 'r', encoding='utf-8') as f:
                cache['main_text'] = f.read()
        else:
            cache['main_text'] = ""

        # 读取 settings/main.txt
        if os.path.exists(MAIN_SETTINGS_FILE):
            with open(MAIN_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = {}
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip().lower()
                        value = value.strip().lower()
                        if key == 'construction':
                            settings['construction'] = (value == 'true')
                cache['settings'] = settings
        else:
            cache['settings'] = {}

        # 加载所有内容到缓存
        load_all_contents_to_cache()
    except Exception as e:
        print(f"初始化缓存时出错: {e}")

    # 启动缓存更新线程
    cache_thread = threading.Thread(target=update_cache, daemon=True)
    cache_thread.start()

    # 启动写入队列处理线程
    write_thread = threading.Thread(target=process_write_queue, daemon=True)
    write_thread.start()

    # 启动 Flask 服务器
    app.run(host='0.0.0.0', port=PORT, threaded=True)
