#!/usr/bin/env python3
"""
VPN Gate SOCKS5 代理管理 Web 界面
"""
from flask import Flask, render_template, jsonify, request
import requests
import csv
import subprocess
import os
import json
from datetime import datetime

app = Flask(__name__)

# 配置文件路径
CONFIG_FILE = '/config/vpn_config.json'
VPN_CLIENT_PATH = '/opt/vpnclient'

class VPNManager:
    def __init__(self):
        self.current_connection = None
        self.load_config()
    
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
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # 解析 CSV（跳过前两行注释）
            lines = response.text.strip().split('\n')[2:]
            reader = csv.DictReader(lines)
            
            servers = []
            for row in reader:
                # 只选择支持 SSL-VPN 的服务器
                if row.get('HostName') and row.get('IP'):
                    server = {
                        'hostname': row.get('HostName', ''),
                        'ip': row.get('IP', ''),
                        'country': row.get('CountryLong', 'Unknown'),
                        'country_code': row.get('CountryShort', ''),
                        'speed': int(row.get('Speed', 0)),
                        'ping': int(row.get('Ping', 0)) if row.get('Ping') else 999,
                        'uptime': int(row.get('Uptime', 0)),
                        'sessions': int(row.get('NumVpnSessions', 0)),
                        'total_users': int(row.get('TotalUsers', 0)),
                        'total_traffic': float(row.get('TotalTraffic', 0)),
                        'log_policy': row.get('LogType', 'Unknown'),
                        'operator': row.get('Operator', 'Anonymous'),
                        'message': row.get('Message', ''),
                        'score': int(row.get('Score', 0)),
                        # SSL-VPN 端口（通常是 443 或其他）
                        'port': 443,
                        'supports_ssl': True
                    }
                    servers.append(server)
            
            # 按分数排序
            servers.sort(key=lambda x: x['score'], reverse=True)
            return servers
        
        except Exception as e:
            print(f"获取服务器列表失败: {e}")
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
            
            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                if result.returncode != 0:
                    print(f"命令执行失败: {' '.join(cmd)}")
                    print(f"错误: {result.stderr.decode()}")
            
            # 等待连接建立
            import time
            time.sleep(5)
            
            # 配置网卡
            subprocess.run(['dhclient', 'vpn_vpn'], timeout=10)
            
            # 重启 SOCKS5 代理
            subprocess.run(['pkill', '-9', 'danted'], timeout=5)
            subprocess.run(['danted', '-f', '/etc/danted.conf'], timeout=5)
            
            self.current_connection = {
                'ip': server_ip,
                'port': server_port,
                'connected_at': datetime.now().isoformat()
            }
            self.save_config()
            
            return True
        
        except Exception as e:
            print(f"连接失败: {e}")
            return False

vpn_manager = VPNManager()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

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
        'message': '连接成功' if success else '连接失败'
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
