#!/usr/bin/env python3
"""
VPN Gate SOCKS5 代理管理 Web 界面
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import requests
import csv
import subprocess
import os
import json
import shutil
import time
import re
import socket
from datetime import datetime
from requests.adapters import HTTPAdapter

app = Flask(__name__)
app.secret_key = os.environ.get('WEB_SESSION_SECRET', 'dev-change-this-secret')

# 配置文件路径
CONFIG_FILE = '/config/vpn_config.json'
VPN_CLIENT_PATH = '/opt/vpnclient'


def check_web_auth():
    """检查 Web 访问认证（通过环境变量开启）"""
    web_password = os.environ.get('WEB_PASSWORD')
    if not web_password:
        return True
    return bool(session.get('web_authed'))


@app.before_request
def require_web_auth():
    """为全部页面和 API 增加认证（非浏览器弹窗）"""
    if check_web_auth():
        return None

    if request.path in ['/login']:
        return None

    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': '未登录或登录已过期'}), 401

    return redirect(url_for('login', next=request.path))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Web 登录页"""
    web_password = os.environ.get('WEB_PASSWORD')
    if not web_password:
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        web_username = os.environ.get('WEB_USERNAME', 'admin')
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        next_path = request.form.get('next', '/')

        if username == web_username and password == web_password:
            session['web_authed'] = True
            return redirect(next_path or '/')

        error = '用户名或密码错误'

    return render_template('login.html', error=error, next=request.args.get('next', '/'))


@app.route('/logout')
def logout():
    """退出登录"""
    session.pop('web_authed', None)
    return redirect(url_for('login'))

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

    def interface_has_ipv4(self, interface_name):
        """检查网卡是否拿到 IPv4 地址"""
        result = subprocess.run(
            ['ip', '-4', 'addr', 'show', interface_name],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False
        return 'inet ' in (result.stdout or '')

    def get_interface_ipv4(self, interface_name):
        """获取网卡 IPv4 地址"""
        result = subprocess.run(
            ['ip', '-4', 'addr', 'show', interface_name],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return None

        match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', result.stdout or '')
        if not match:
            return None
        return match.group(1)

    def get_account_session_status(self):
        """读取 SoftEther 账户会话状态"""
        result = subprocess.run(
            [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 'AccountStatusGet', 'vpngate'],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = (result.stdout or '') + '\n' + (result.stderr or '')

        if 'Session Status' in output:
            if 'Connected' in output:
                return 'Connected', None
            if 'Retrying' in output:
                return 'Retrying', output.strip()
            if 'Disconnected' in output:
                return 'Disconnected', output.strip()

        return 'Unknown', output.strip()

    def probe_vpn_egress(self, source_ip):
        """真实出网探测：绑定 VPN 网卡 IP 发起 HTTPS 请求"""
        def tcp_probe(host, port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                sock.bind((source_ip, 0))
                sock.connect((host, port))
                return True, None
            except Exception as e:
                return False, str(e)
            finally:
                try:
                    sock.close()
                except Exception:
                    pass

        tcp_targets = [
            ('1.1.1.1', 443),
            ('8.8.8.8', 53),
            ('9.9.9.9', 53)
        ]

        tcp_last_error = None
        for host, port in tcp_targets:
            ok, err = tcp_probe(host, port)
            if ok:
                return True, None
            tcp_last_error = f'{host}:{port} 连接失败: {err}'

        # 如果 TCP 探测全部失败，再尝试 HTTPS 探测（更严格）
        class SourceAddressAdapter(HTTPAdapter):
            def __init__(self, bind_ip, **kwargs):
                self.bind_ip = bind_ip
                super().__init__(**kwargs)

            def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
                pool_kwargs['source_address'] = (self.bind_ip, 0)
                return super().init_poolmanager(connections, maxsize, block, **pool_kwargs)

        session = requests.Session()
        session.mount('http://', SourceAddressAdapter(source_ip))
        session.mount('https://', SourceAddressAdapter(source_ip))

        probe_urls = [
            'https://ipv4.ip.sb',
            'https://api.ipify.org'
        ]

        last_error = None
        for url in probe_urls:
            try:
                resp = session.get(url, timeout=8)
                if resp.status_code == 200 and resp.text.strip():
                    return True, None
                last_error = f'{url} 返回状态码 {resp.status_code}'
            except Exception as e:
                last_error = f'{url} 请求失败: {e}'

        return False, last_error or tcp_last_error or '出网探测失败'

    def check_tun_ready(self):
        """检查 TUN 设备是否可用"""
        tun_path = '/dev/net/tun'
        if not os.path.exists(tun_path):
            return False, (
                '容器内缺少 /dev/net/tun，无法创建 SoftEther 虚拟网卡。'
                '通常需要在原生 Linux/支持 TUN 的环境运行（Windows Docker Desktop 常见此问题）。'
            )

        if not os.access(tun_path, os.R_OK | os.W_OK):
            return False, '容器对 /dev/net/tun 没有读写权限，请检查 Docker 权限配置'

        return True, None
    
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

    def run_vpncmd(self, args, timeout=15):
        """执行 vpncmd 并返回 (ok, output)"""
        cmd = [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD'] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        output = ((result.stdout or '') + '\n' + (result.stderr or '')).strip()
        return result.returncode == 0, output
    
    def disconnect(self):
        """断开当前连接"""
        try:
            ok, out = self.run_vpncmd(['AccountDisconnect', 'vpngate'], timeout=10)
            if not ok and 'Error code: 36' not in out:
                print(f"AccountDisconnect 失败: {out}")

            ok, out = self.run_vpncmd(['AccountDelete', 'vpngate'], timeout=10)
            if not ok and 'Error code: 36' not in out:
                print(f"AccountDelete 失败: {out}")

            return True
        except Exception as e:
            print(f"断开连接失败: {e}")
            return False

    def start_socks_proxy(self):
        """启动 SOCKS5 代理（非阻塞）"""
        try:
            if shutil.which('pkill'):
                subprocess.run(['pkill', '-9', 'danted'], timeout=5)

            proc = subprocess.Popen(
                ['danted', '-f', '/etc/danted.conf'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            time.sleep(1)

            if proc.poll() is not None:
                stderr = (proc.stderr.read() or '').strip() if proc.stderr else ''
                stdout = (proc.stdout.read() or '').strip() if proc.stdout else ''
                err_msg = stderr or stdout or 'danted 启动失败'
                return False, err_msg

            return True, None
        except Exception as e:
            return False, str(e)
    
    def connect(self, server_ip, server_port=443):
        """连接到指定服务器"""
        try:
            self.last_error = None

            tun_ok, tun_error = self.check_tun_ready()
            if not tun_ok:
                self.last_error = tun_error
                print(self.last_error)
                return False

            # 先断开现有连接
            self.disconnect()
            
            # 创建新连接
            steps = [
                ('NicDelete', ['NicDelete', 'vpn']),
                ('NicCreate', ['NicCreate', 'vpn']),
                (
                    'AccountCreate',
                    [
                        'AccountCreate', 'vpngate',
                        f'/SERVER:{server_ip}:{server_port}',
                        '/HUB:VPNGATE',
                        '/USERNAME:vpn',
                        '/NICNAME:vpn'
                    ]
                ),
                ('AccountPasswordSet', ['AccountPasswordSet', 'vpngate', '/PASSWORD:vpn', '/TYPE:standard']),
                ('AccountConnect', ['AccountConnect', 'vpngate'])
            ]

            for step_name, args in steps:
                ok, out = self.run_vpncmd(args, timeout=15)

                # NicDelete 在首次连接时失败是正常情况
                if step_name == 'NicDelete' and not ok:
                    continue

                # 账户已存在则先删除再重建一次
                if step_name == 'AccountCreate' and (not ok) and 'Error code: 34' in out:
                    self.run_vpncmd(['AccountDisconnect', 'vpngate'], timeout=10)
                    self.run_vpncmd(['AccountDelete', 'vpngate'], timeout=10)
                    ok, out = self.run_vpncmd(args, timeout=15)

                if not ok:
                    err_msg = out or 'unknown error'
                    if 'Error code: 31' in err_msg:
                        err_msg = (
                            'NicCreate 失败（Error code: 31），通常是容器无法访问 TUN/TAP。'
                            '请确认使用 Linux 内核并启用 /dev/net/tun 与特权权限。'
                        )
                    self.last_error = f"vpncmd 失败: {err_msg}"
                    print(f"命令执行失败: {step_name}")
                    print(f"错误: {err_msg}")
                    return False
            
            # 等待连接建立
            time.sleep(5)
            
            if not self.interface_exists('vpn_vpn'):
                self.last_error = 'VPN 虚拟网卡 vpn_vpn 未建立，连接可能未成功'
                print(self.last_error)
                return False

            # 配置网卡（镜像里通常是 dhcpcd5，不一定有 dhclient）
            if shutil.which('dhclient'):
                dhcp_result = subprocess.run(
                    ['dhclient', 'vpn_vpn'],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
            elif shutil.which('dhcpcd'):
                dhcp_result = subprocess.run(
                    ['dhcpcd', 'vpn_vpn'],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
            else:
                print("警告: 未找到 dhclient/dhcpcd，跳过网卡 DHCP 配置")
                dhcp_result = None

            if dhcp_result is not None and dhcp_result.returncode != 0:
                err_msg = (dhcp_result.stderr or dhcp_result.stdout or '').strip() or 'DHCP 配置失败'
                self.last_error = f'VPN 网卡配置失败: {err_msg}'
                print(self.last_error)
                return False

            if not self.interface_has_ipv4('vpn_vpn'):
                self.last_error = 'VPN 虚拟网卡已创建但未获取到 IPv4 地址，无法转发流量'
                print(self.last_error)
                return False

            vpn_ip = self.get_interface_ipv4('vpn_vpn')
            if not vpn_ip:
                self.last_error = '无法读取 VPN 虚拟网卡 IPv4 地址'
                print(self.last_error)
                return False

            if vpn_ip.startswith('169.254.'):
                self.last_error = 'VPN 虚拟网卡只拿到链路本地地址(169.254.x.x)，VPN 实际未连通'
                print(self.last_error)
                return False

            session_status, session_output = self.get_account_session_status()
            if session_status != 'Connected':
                self.last_error = f'VPN 会话未建立，当前状态: {session_status}'
                if session_output:
                    self.last_error += f'\n{session_output}'
                print(self.last_error)
                return False

            probe_ok, probe_error = self.probe_vpn_egress(vpn_ip)
            if not probe_ok:
                self.last_error = f'VPN 真实出网探测失败: {probe_error}'
                print(self.last_error)
                return False
            
            # 重启 SOCKS5 代理（避免前台进程阻塞导致超时）
            socks_ok, socks_error = self.start_socks_proxy()
            if not socks_ok:
                self.last_error = f'SOCKS5 启动失败: {socks_error}'
                print(self.last_error)
                return False
            
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
