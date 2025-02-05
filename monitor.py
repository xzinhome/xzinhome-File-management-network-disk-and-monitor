from flask import Flask, render_template, request, send_file, redirect, url_for, session, jsonify
from functools import wraps
import psutil
import os
import time
from werkzeug.utils import secure_filename
import threading
from datetime import datetime
import zipfile
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于session加密
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # 文件上传目录
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 最大16GB

# 密码设置
PASSWORD = ""

# 确保上传目录存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_size_format(bytes):
    """将字节转换为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
from flask import Flask, render_template, request, send_file, redirect, url_for, session, jsonify
from functools import wraps
import psutil
import os
import time
from werkzeug.utils import secure_filename
import threading
from datetime import datetime
import zipfile
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于session加密
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # 文件上传目录
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 最大16GB

# 密码设置
PASSWORD = ""

# 确保上传目录存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_size_format(bytes):
    """将字节转换为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024

def get_network_usage():
    """获取网络使用情况"""
    net_io = psutil.net_io_counters()
    return {
        'bytes_sent': get_size_format(net_io.bytes_sent),
        'bytes_recv': get_size_format(net_io.bytes_recv),
        'speed_sent': get_size_format(net_io.bytes_sent / time.time()),
        'speed_recv': get_size_format(net_io.bytes_recv / time.time())
    }

def get_file_type(filename):
    """获取文件类型"""
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return 'image'
    elif ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm']:
        return 'video'
    elif ext in ['.txt', '.md', '.log']:
        return 'text'
    return 'other'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error="密码错误")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    network = get_network_usage()
    
    return render_template('index.html',
                         cpu_percent=cpu_percent,
                         memory_percent=memory.percent,
                         disk_percent=disk.percent,
                         network=network)

# 添加文件管理主页路由
@app.route('/files')
@login_required
def files():
    files = []
    for item in os.listdir(app.config['UPLOAD_FOLDER']):
        item_path = os.path.join(app.config['UPLOAD_FOLDER'], item)
        if os.path.isdir(item_path):
            files.append({
                'name': item,
                'type': 'folder',
                'size': '',
                'path': item
            })
        else:
            file_type = get_file_type(item)
            size = get_size_format(os.path.getsize(item_path))
            files.append({
                'name': item,
                'type': file_type,
                'size': size,
                'path': item
            })
    
    return render_template('files.html', files=files)

# 修改上传文件大小限制和允许的文件类型
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16GB
ALLOWED_EXTENSIONS = {
    'image': {'.jpg', '.jpeg', '.png', '.gif', '.webp'},
    'video': {'.mp4', '.avi', '.mkv', '.mov', '.webm'},
    'text': {'.txt', '.md', '.log'},
    'document': {'.pdf', '.doc', '.docx', '.xls', '.xlsx'},
    'other': {'.zip', '.rar', '.7z'}
}

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return any(ext in types for types in ALLOWED_EXTENSIONS.values())

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return {'error': '没有选择文件'}, 400
    
    file = request.files['file']
    if file.filename == '':
        return {'error': '没有选择文件'}, 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            # 添加时间戳避免文件名冲突
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{name}_{timestamp}{ext}"
            
            # 获取当前文件夹路径（如果有的话）
            current_folder = request.form.get('current_folder', '')
            if current_folder:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], current_folder, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
            else:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            return {'success': True, 'filename': filename}, 200
        except Exception as e:
            return {'error': f'上传失败: {str(e)}'}, 500
    else:
        return {'error': '不支持的文件类型'}, 400

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename),
                    as_attachment=True)

@app.route('/view/<filename>')
@login_required
def view_file(filename):
    file_type = get_file_type(filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if file_type == 'text':
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template('view_text.html', content=content, filename=filename)
    elif file_type in ['image', 'video']:
        return render_template('view_media.html', 
                             filename=filename, 
                             file_type=file_type)
    else:
        return redirect(url_for('download_file', filename=filename))

@app.route('/delete/<path:filename>')
@login_required
def delete_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            # 修改重定向目标
            if '/' in filename:
                parent_folder = os.path.dirname(filename)
                return redirect(url_for('browse_folder', folder_path=parent_folder))
            return redirect(url_for('files'))
        return redirect(url_for('files'))
    except Exception as e:
        return render_template('error.html', error=f'删除文件失败: {str(e)}')

@app.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    folder_name = request.form.get('folder_name')
    current_folder = request.form.get('current_folder', '')
    
    if not folder_name:
        return {'error': '请输入文件夹名称'}, 400
    
    try:
        # 安全处理文件夹名称
        folder_name = secure_filename(folder_name)
        if current_folder:
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], current_folder, folder_name)
        else:
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        
        if os.path.exists(folder_path):
            return {'error': '文件夹已存在'}, 400
            
        os.makedirs(folder_path)
        return {'success': True, 'folder_name': folder_name}, 200
    except Exception as e:
        return {'error': f'创建文件夹失败: {str(e)}'}, 500

@app.route('/delete_folder/<path:folder_name>')
@login_required
def delete_folder(folder_name):
    try:
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            import shutil
            shutil.rmtree(folder_path)
            # 修改重定向目标
            if '/' in folder_name:
                parent_folder = os.path.dirname(folder_name)
                return redirect(url_for('browse_folder', folder_path=parent_folder))
            return redirect(url_for('files'))
        return redirect(url_for('files'))
    except Exception as e:
        return render_template('error.html', error=f'删除文件夹失败: {str(e)}')

@app.route('/folder/<path:folder_path>')
@login_required
def browse_folder(folder_path):
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], folder_path)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return redirect(url_for('index'))
    
    files = []
    for item in os.listdir(full_path):
        item_path = os.path.join(full_path, item)
        if os.path.isdir(item_path):
            files.append({
                'name': item,
                'type': 'folder',
                'size': '',
                'path': os.path.join(folder_path, item)
            })
        else:
            file_type = get_file_type(item)
            size = get_size_format(os.path.getsize(item_path))
            files.append({
                'name': item,
                'type': file_type,
                'size': size,
                'path': os.path.join(folder_path, item)
            })
    
    return render_template('folder.html',
                         current_folder=folder_path,
                         files=files)

@app.route('/system_info')
@login_required
def system_info():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    network = get_network_usage()
    
    return jsonify({
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk.percent,
        'network': network
    })

@app.route('/rename', methods=['POST'])
@login_required
def rename_item():
    old_path = request.form.get('old_path')
    new_name = request.form.get('new_name')
    if not old_path or not new_name:
        return {'error': '参数错误'}, 400
    
    try:
        old_full_path = os.path.join(app.config['UPLOAD_FOLDER'], old_path)
        new_name = secure_filename(new_name)
        new_path = os.path.join(os.path.dirname(old_full_path), new_name)
        
        if os.path.exists(new_path):
            return {'error': '文件名已存在'}, 400
            
        os.rename(old_full_path, new_path)
        return {'success': True, 'new_name': new_name}, 200
    except Exception as e:
        return {'error': f'重命名失败: {str(e)}'}, 500

@app.route('/compress', methods=['POST'])
@login_required
def compress_files():
    files = request.form.getlist('files[]')
    zip_name = request.form.get('zip_name', 'archive.zip')
    
    if not files:
        return {'error': '请选择要压缩的文件'}, 400
    
    try:
        zip_name = secure_filename(zip_name)
        if not zip_name.endswith('.zip'):
            zip_name += '.zip'
            
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_name)
        memory_file = BytesIO()
        
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in files:
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], file_path)
                if os.path.exists(full_path):
                    if os.path.isfile(full_path):
                        zf.write(full_path, os.path.basename(file_path))
                    elif os.path.isdir(full_path):
                        for root, dirs, filenames in os.walk(full_path):
                            for filename in filenames:
                                file_full_path = os.path.join(root, filename)
                                arc_name = os.path.relpath(file_full_path, os.path.dirname(full_path))
                                zf.write(file_full_path, arc_name)
        
        memory_file.seek(0)
        with open(zip_path, 'wb') as f:
            f.write(memory_file.getvalue())
            
        return {'success': True, 'zip_name': zip_name}, 200
    except Exception as e:
        return {'error': f'压缩失败: {str(e)}'}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 
