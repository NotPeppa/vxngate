#!/usr/bin/env python3
"""
VPN Gate SOCKS5 代理管理 Web 界面
"""
from flask import Flask, render_template, jsonify, request, Response
import requests
import csv
import subprocess
import os
import json
import shutil
from datetime import datetime

app = Flask(__name__)

# 配置文件路径
CONFIG_FILE = '/config/vpn_config.json'
VPN_CLIENT_PATH = '/opt/vpnclient'


def check_web_auth():
    """检查 Web 访问认证（通过环境变量开启）"""
    web_password = os.environ.get('WEB_PASSWORD')
    if not web_password:
        return True

    web_username = os.environ.get('WEB_USERNAME', 'admin')
    auth = request.authorization
    if not auth:
        return False

    return auth.username == web_username and auth.password == web_password


@app.before_request
def require_web_auth():
    """为全部页面和 API 增加基础认证"""
    if check_web_auth():
        return None

    return Response(
        'Authentication required',
        401,
        {'WWW-Authenticate': 'Basic realm="VPN Gate Admin"'}
    )

class VPNManager:
    def __init__(self):
        self.current_connection = None
        self.last_error = None
        self.load_config()

    def interface_exists(self, interface_name):
        """检查网卡是否存在"""
        result = subprocess.run(
            ['ip', 'link', 'show', interface_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    
    def load_config(self):
        """加载配置"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.current_connection = config.get('current_connection')
    
    def save_config(self):
        """保存配置"""
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                'current_connection': self.current_connection,
                'last_updated': datetime.now().isoformat()
            }, f)
    
    def get_vpngate_servers(self):
        """从 VPN Gate 获取服务器列表"""
        try:
            # VPN Gate CSV API
            url = 'https://www.vpngate.net/api/iphone/'
            print(f"正在从 {url} 获取服务器列表...")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            print(f"响应状态码: {response.status_code}")
            print(f"响应长度: {len(response.text)} 字符")
            
            # 解析 CSV（跳过前两行注释）
            # VPN Gate 返回格式：第1行是 *vpn_servers，第2行是 #开头的表头，第3行开始是数据
            lines = response.text.strip().split('\n')
            print(f"总行数: {len(lines)}")
            print(f"前3行内容: {lines[:3] if len(lines) >= 3 else lines}")
            
            if len(lines) < 3:
                print("错误: CSV 数据行数不足")
                return []
            
            # 跳过第1行(*vpn_servers)，从第2行开始（#开头的表头）
            # 移除表头的 # 号
            csv_data = lines[1:]  # 从第2行开始
            if csv_data[0].startswith('#'):
                csv_data[0] = csv_data[0][1:]  # 移除表头的 # 号
            
            print(f"CSV 表头: {csv_data[0][:100]}")
            print(f"CSV 数据行数: {len(csv_data) - 1}")
            
            # 使用 csv.DictReader 解析
            reader = csv.DictReader(csv_data)
            
            servers = []
            for idx, row in enumerate(reader):
                try:
                    # 调试：打印第一行的所有字段名
                    if idx == 0:
                        print(f"CSV字段名: {list(row.keys())}")
                    
                    # 只选择支持 SSL-VPN 的服务器
                    if row.get('HostName') and row.get('IP'):
                        # 兼容 TotalUser 和 TotalUsers 两种字段名
                        total_users = row.get('TotalUsers') or row.get('TotalUser', 0)
                        
                        # 安全解析数值字段（可能包含'-'或空值）
                        def safe_int(value, default=0):
                            try:
                                return int(value) if value and value != '-' else default
                            except (ValueError, TypeError):
                                return default
                        
                        def safe_float(value, default=0.0):
                            try:
                                return float(value) if value and value != '-' else default
                            except (ValueError, TypeError):
                                return default
                        
                        server = {
                            'hostname': row.get('HostName', ''),
                            'ip': row.get('IP', ''),
                            'country': row.get('CountryLong', 'Unknown'),
                            'country_code': row.get('CountryShort', ''),
                            'speed': safe_int(row.get('Speed'), 0),
                            'ping': safe_int(row.get('Ping'), 999),
                            'uptime': safe_int(row.get('Uptime'), 0),
                            'sessions': safe_int(row.get('NumVpnSessions'), 0),
                            'total_users': safe_int(total_users, 0),
                            'total_traffic': safe_float(row.get('TotalTraffic'), 0.0),
                            'log_policy': row.get('LogType', 'Unknown'),
                            'operator': row.get('Operator', 'Anonymous'),
                            'message': row.get('Message', ''),
                            'score': int(row.get('Score', 0) or 0),
                            # SSL-VPN 端口（通常是 443 或其他）
                            'port': 443,
                            'supports_ssl': True
                        }
                        servers.append(server)
                except Exception as e:
                    print(f"解析第 {idx} 行失败: {e}")
                    continue
            
            print(f"成功解析 {len(servers)} 个服务器")
            
            # 按分数排序
            servers.sort(key=lambda x: x['score'], reverse=True)
            return servers
        
        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return []
        except Exception as e:
            print(f"获取服务器列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_status(self):
        """获取当前 VPN 连接状态"""
        try:
            result = subprocess.run(
                [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 'AccountList'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # 解析输出判断是否已连接
            output = result.stdout
            is_connected = 'Connected' in output or '已连接' in output
            
            return {
                'connected': is_connected,
                'current_server': self.current_connection,
                'socks_port': 1080
            }
        except Exception as e:
            print(f"获取状态失败: {e}")
            return {
                'connected': False,
                'current_server': None,
                'socks_port': 1080
            }
    
    def disconnect(self):
        """断开当前连接"""
        try:
            if self.current_connection:
                subprocess.run(
                    [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 
                     'AccountDisconnect', 'vpngate'],
                    timeout=10
                )
                subprocess.run(
                    [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 
                     'AccountDelete', 'vpngate'],
                    timeout=10
                )
            return True
        except Exception as e:
            print(f"断开连接失败: {e}")
            return False
    
    def connect(self, server_ip, server_port=443):
        """连接到指定服务器"""
        try:
            self.last_error = None
            # 先断开现有连接
            self.disconnect()
            
            # 创建新连接
            commands = [
                # 删除旧的虚拟网卡（如果存在）
                [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 'NicDelete', 'vpn'],
                # 创建虚拟网卡
                [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 'NicCreate', 'vpn'],
                # 创建账户
                [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 
                 'AccountCreate', 'vpngate', 
                 f'/SERVER:{server_ip}:{server_port}', 
                 '/HUB:VPNGATE', 
                 '/USERNAME:vpn', 
                 '/NICNAME:vpn'],
                # 设置密码
                [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 
                 'AccountPasswordSet', 'vpngate', 
                 '/PASSWORD:vpn', 
                 '/TYPE:standard'],
                # 连接
                [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 
                 'AccountConnect', 'vpngate']
            ]
            
            for idx, cmd in enumerate(commands):
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                # 第一个命令 NicDelete 在首次连接时失败是正常情况
                if idx == 0 and result.returncode != 0:
                    continue

                if result.returncode != 0:
                    stderr = (result.stderr or '').strip()
                    stdout = (result.stdout or '').strip()
                    err_msg = stderr or stdout or 'unknown error'
                    self.last_error = f"vpncmd 失败: {err_msg}"
                    print(f"命令执行失败: {' '.join(cmd)}")
                    print(f"错误: {err_msg}")
                    return False
            
            # 等待连接建立
            import time
            time.sleep(5)
            
            if not self.interface_exists('vpn_vpn'):
                self.last_error = 'VPN 虚拟网卡 vpn_vpn 未建立，连接可能未成功'
                print(self.last_error)
                return False

            # 配置网卡（镜像里通常是 dhcpcd5，不一定有 dhclient）
            if shutil.which('dhclient'):
                subprocess.run(['dhclient', 'vpn_vpn'], timeout=15)
            elif shutil.which('dhcpcd'):
                subprocess.run(['dhcpcd', 'vpn_vpn'], timeout=15)
            else:
                print("警告: 未找到 dhclient/dhcpcd，跳过网卡 DHCP 配置")
            
            # 重启 SOCKS5 代理
            if shutil.which('pkill'):
                subprocess.run(['pkill', '-9', 'danted'], timeout=5)
            subprocess.run(['danted', '-f', '/etc/danted.conf'], timeout=5)
            
            self.current_connection = {
                'ip': server_ip,
                'port': server_port,
                'connected_at': datetime.now().isoformat()
            }
            self.save_config()
            self.last_error = None
            
            return True
        
        except Exception as e:
            self.last_error = str(e)
            print(f"连接失败: {e}")
            return False

vpn_manager = VPNManager()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/test')
def test_api():
    """测试 VPN Gate API 连接"""
    try:
        url = 'https://www.vpngate.net/api/iphone/'
        response = requests.get(url, timeout=10)
        
        return jsonify({
            'success': True,
            'status_code': response.status_code,
            'content_length': len(response.text),
            'first_100_chars': response.text[:100]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/servers')
def get_servers():
    """获取服务器列表"""
    servers = vpn_manager.get_vpngate_servers()
    return jsonify({
        'success': True,
        'servers': servers,
        'count': len(servers)
    })

@app.route('/api/status')
def get_status():
    """获取连接状态"""
    status = vpn_manager.get_status()
    return jsonify({
        'success': True,
        'status': status
    })

@app.route('/api/connect', methods=['POST'])
def connect():
    """连接到服务器"""
    data = request.json
    server_ip = data.get('ip')
    server_port = data.get('port', 443)
    
    if not server_ip:
        return jsonify({
            'success': False,
            'error': '缺少服务器 IP'
        }), 400
    
    success = vpn_manager.connect(server_ip, server_port)
    
    return jsonify({
        'success': success,
        'message': '连接成功' if success else '连接失败',
        'error': None if success else vpn_manager.last_error
    })

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """断开连接"""
    success = vpn_manager.disconnect()
    
    if success:
        vpn_manager.current_connection = None
        vpn_manager.save_config()
    
    return jsonify({
        'success': success,
        'message': '已断开连接' if success else '断开失败'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
