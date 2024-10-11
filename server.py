from flask import Flask, request, jsonify, send_from_directory, Response
import sqlite3
import re
import os
import logging
from functools import wraps
from datetime import datetime

app = Flask(__name__)

DATABASE = 'content.db'
MAIN_TEXT_FILE = 'main.txt'
PORT = 19998
META_FOLDER = 'meta'
LOG_FILE = 'log.log'
FAVICON_FILE = 'favicon.ico'

ID_REGEX = re.compile(r'^[A-Za-z0-9]{3,24}$')

log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True

logger = logging.getLogger('custom_logger')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE)
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

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
        

        initial_data = [
            ('dqjl', 'hi y'),
        ]
        c.executemany('INSERT OR IGNORE INTO contents (id, content) VALUES (?, ?)', initial_data)
        conn.commit()
        conn.close()
        print("数据库已初始化。")
    else:
        print("数据库已存在。")

def init_main_txt():
    if not os.path.exists(MAIN_TEXT_FILE):
        with open(MAIN_TEXT_FILE, 'w', encoding='utf-8') as f:
            f.write("这是 main.txt 的内容。")
        print("main.txt 已创建。")
    else:
        print("main.txt 已存在。")

def init_meta():
    if not os.path.exists(META_FOLDER):
        os.makedirs(META_FOLDER)
        print(f"{META_FOLDER} 文件夹已创建。")
    

    bg_path = os.path.join(META_FOLDER, 'bg.png')
    if not os.path.exists(bg_path):
        try:
            from PIL import Image
            img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
            img.save(bg_path)
            print(f"{bg_path} 已创建。请替换为您需要的背景图片。")
        except ImportError:
            print("Pillow 未安装，无法创建占位图片。请手动添加 meta/bg.png。")

def init_favicon():
    if not os.path.exists(FAVICON_FILE):
        try:
            from PIL import Image
            img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            img.save(FAVICON_FILE)
            print(f"{FAVICON_FILE} 已创建。请替换为您需要的 favicon.ico。")
        except ImportError:
            print("Pillow 未安装，无法创建占位 favicon.ico。请手动添加 favicon.ico。")

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_content(identifier):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT content FROM contents WHERE id = ?', (identifier,))
    row = c.fetchone()
    conn.close()
    if row:
        return row['content']
    else:
        return ""  


def upsert_content(identifier, new_content):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO contents (id, content) VALUES (?, ?)
        ON CONFLICT(id) DO UPDATE SET content=excluded.content
    ''', (identifier, new_content))
    conn.commit()
    conn.close()

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

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@log_request
def serve_content(path):
    

    if path in ['', '0', '1', 'main', 'index']:
        try:
            with open(MAIN_TEXT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            content = ""
        display_path = '/' if path == '' else f'/{path}'
        return render_html(content, read_only=True, path=display_path)
    
    

    if ID_REGEX.fullmatch(path):
        identifier = path
        content = get_content(identifier)
        display_path = f'/{identifier}'
        return render_html(content, read_only=False, path=display_path, identifier=identifier)
    
    

    return "404 Not Found", 404

@app.route('/update/<identifier>', methods=['POST'])
@log_request
def update(identifier):
    

    if not ID_REGEX.fullmatch(identifier):
        return jsonify({'status': 'error', 'message': '无效的标识符。'}), 400
    
    

    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({'status': 'error', 'message': '缺少内容。'}), 400
    
    new_content = data['content']
    upsert_content(identifier, new_content)
    return jsonify({'status': 'success', 'message': '内容已更新。'})

@app.route('/meta/<path:filename>')
@log_request
def meta_static(filename):
    return send_from_directory(META_FOLDER, filename)

@app.route('/favicon.ico')
@log_request
def favicon():
    if os.path.exists(FAVICON_FILE):
        return send_from_directory('.', FAVICON_FILE)
    else:
        return "", 204  


def render_html(content, read_only=False, path='/', identifier=None):
    

    css = """
    <style>
    @media screen {
      body {
        background:url(/meta/bg.png) top left repeat 

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
        background-color:

        border-radius:3.456789px;
        border:1px solid 

        box-shadow:0 0 5px 0 

      }
      .flag {
        position:fixed;
        left:0;
        right:0;
        bottom:1em;
        height:.8em;
        text-align:center;
        color:

        font-size:14px
      }
      a:link,
      a:visited,
      a:active {
        color:

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
        color:

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
        color:

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
      background-color:

      color:

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

    js = f"""
    <script>
    (function(){{
        document.addEventListener('DOMContentLoaded', function() {{
            const contentArea = document.getElementById('content');
            let lastContent = contentArea.value;

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
        }});
    }})();
    </script>
    """

    

    flag = f'''
    <a href="https://github.com/lightworld689/justgetmytext" target="_blank">JustGetMyText</a> - {path}
    '''
    if read_only:
        flag += " - ReadOnly"

    

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>内容查看与编辑</title>
        {css}
    </head>
    <body>
        <div class="stack">
            <div class="layer">
                <textarea id="content" class="content" {'readonly' if read_only else ''} style="height:100%; width:100%;">{content}</textarea>
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

if __name__ == '__main__':
    

    init_db()
    init_main_txt()
    init_meta()
    init_favicon()

    

    app.run(host='0.0.0.0', port=PORT, threaded=True)
