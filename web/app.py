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
import ssl
from datetime import datetime

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
        self.last_warning = None
        self.servers_cache = None
        self.servers_cache_at = None
        self.load_config()

    def _bind_socket_to_vpn(self, sock):
        """尽量将 socket 绑定到 VPN 网卡，避免走错路由"""
        bind_opt = getattr(socket, 'SO_BINDTODEVICE', None)
        if bind_opt is None:
            return
        try:
            sock.setsockopt(socket.SOL_SOCKET, bind_opt, b'vpn_vpn\0')
        except Exception:
            pass

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

    def wait_for_session_connected(self, timeout=25, poll_interval=2):
        """轮询 SoftEther 会话状态，直到 Connected 或超时"""
        deadline = time.time() + timeout
        last_status = 'Unknown'
        last_detail = None
        while True:
            status, detail = self.get_account_session_status()
            last_status = status
            last_detail = detail
            if status == 'Connected':
                return True, status, None
            if time.time() >= deadline:
                return False, last_status, last_detail
            time.sleep(poll_interval)

    def get_packet_stats(self):
        """解析 AccountStatusGet 的收发包计数，用于 DHCP 诊断"""
        try:
            result = subprocess.run(
                [f'{VPN_CLIENT_PATH}/vpncmd', 'localhost', '/CLIENT', '/CMD', 'AccountStatusGet', 'vpngate'],
                capture_output=True,
                text=True,
                timeout=10
            )
        except Exception:
            return {}

        output = result.stdout or ''
        stats = {}
        patterns = {
            'out_bcast': r'Outgoing Broadcast Packets\s*\|\s*([\d,]+)',
            'in_bcast': r'Incoming Broadcast Packets\s*\|\s*([\d,]+)',
            'out_unicast': r'Outgoing Unicast Packets\s*\|\s*([\d,]+)',
            'in_unicast': r'Incoming Unicast Packets\s*\|\s*([\d,]+)',
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                try:
                    stats[key] = int(match.group(1).replace(',', ''))
                except ValueError:
                    pass
        return stats

    def _flush_interface_ipv4(self, interface):
        """清空接口上已分配的 IPv4 地址，便于 DHCP 重试"""
        try:
            subprocess.run(
                ['ip', '-4', 'addr', 'flush', 'dev', interface],
                capture_output=True,
                text=True,
                timeout=5
            )
        except Exception:
            pass

    def run_dhcp(self, interface='vpn_vpn', attempts=3, per_attempt_timeout=10):
        """
        运行 DHCP，最多重试若干次。
        关键点：
          - udhcpc 优先（行为简单、不做 APIPA 回落）
          - dhcpcd 加 -L 禁用 IPv4LL，避免 DHCP 失败时静默分配 169.254
          - 每次重试前先清空接口地址，避免前次 169.254 残留误导判断
        """
        def build_cmd():
            if shutil.which('udhcpc'):
                return [
                    'udhcpc',
                    '-i', interface,
                    '-n',
                    '-q',
                    '-t', '3',
                    '-T', '2',
                    '-f',
                ]
            if shutil.which('dhcpcd'):
                return [
                    'dhcpcd',
                    '-B',
                    '-4',
                    '-L',
                    '-t', str(per_attempt_timeout),
                    interface,
                ]
            if shutil.which('dhclient'):
                return ['dhclient', '-1', '-v', interface]
            return None

        cmd = build_cmd()
        if cmd is None:
            return False, '未安装 udhcpc/dhcpcd/dhclient，无法执行 DHCP'

        dhcp_tool = cmd[0]
        last_error = None

        for attempt in range(1, attempts + 1):
            if attempt > 1:
                self._flush_interface_ipv4(interface)
                time.sleep(1)

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=per_attempt_timeout + 5,
                )
                stderr = (result.stderr or '').strip()
                stdout = (result.stdout or '').strip()

                if result.returncode == 0:
                    ip = self.get_interface_ipv4(interface)
                    if ip and not ip.startswith('169.254.'):
                        return True, None
                    last_error = (
                        f'[{dhcp_tool} 第 {attempt}/{attempts} 次] '
                        f'命令返回成功但未拿到有效 IP（当前: {ip or "无"}）'
                    )
                else:
                    err_detail = stderr or stdout or f'exit {result.returncode}'
                    last_error = f'[{dhcp_tool} 第 {attempt}/{attempts} 次] 失败: {err_detail}'
            except subprocess.TimeoutExpired:
                last_error = f'[{dhcp_tool} 第 {attempt}/{attempts} 次] 执行超时（>{per_attempt_timeout + 5}s）'
            except Exception as e:
                last_error = f'[{dhcp_tool} 第 {attempt}/{attempts} 次] 异常: {e}'

            print(last_error)

        return False, last_error or f'{dhcp_tool} 尝试 {attempts} 次均失败'

    def probe_vpn_egress(self, source_ip):
        """真实出网探测：绑定 VPN 网卡 IP 发起 IPv4 出站请求"""
        def tcp_probe(host, port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                self._bind_socket_to_vpn(sock)
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

        def http_probe(host, port=80, path='/', use_tls=False):
            request_data = (
                f'GET {path} HTTP/1.1\r\n'
                f'Host: {host}\r\n'
                'User-Agent: vpngate-egress-probe/1.0\r\n'
                'Connection: close\r\n\r\n'
            ).encode('ascii')

            try:
                addr_infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
            except Exception as e:
                return False, f'{host}:{port} IPv4 解析失败: {e}'

            last_err = None
            for family, socktype, proto, _, sockaddr in addr_infos:
                sock = socket.socket(family, socktype, proto)
                sock.settimeout(8)
                try:
                    self._bind_socket_to_vpn(sock)
                    sock.bind((source_ip, 0))
                    sock.connect(sockaddr)

                    conn = sock
                    if use_tls:
                        context = ssl.create_default_context()
                        conn = context.wrap_socket(sock, server_hostname=host)

                    conn.sendall(request_data)
                    response = conn.recv(256)
                    if b' 200 ' in response or b' 204 ' in response:
                        return True, None

                    first_line = response.splitlines()[0].decode('ascii', errors='ignore') if response else '空响应'
                    last_err = f'{host}:{port} 返回异常: {first_line}'
                except Exception as e:
                    last_err = f'{host}:{port} 请求失败: {e}'
                finally:
                    try:
                        sock.close()
                    except Exception:
                        pass

            return False, last_err or f'{host}:{port} 请求失败'

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

        probe_targets = [
            ('ipv4.ip.sb', 443, '/', True),
            ('api.ipify.org', 443, '/', True),
            ('ipv4.ip.sb', 80, '/', False),
            ('api.ipify.org', 80, '/', False),
        ]

        http_errors = []
        for host, port, path, use_tls in probe_targets:
            ok, err = http_probe(host, port=port, path=path, use_tls=use_tls)
            if ok:
                return True, None
            if err:
                http_errors.append(err)

        error_parts = []
        if tcp_last_error:
            error_parts.append(f'TCP 探测失败: {tcp_last_error}')
        if http_errors:
            error_parts.append(f'HTTP 探测失败: {http_errors[-1]}')

        return False, '；'.join(error_parts) or '出网探测失败'

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

    def verify_socks_proxy(self):
        """校验本地 SOCKS5 代理是否可实际转发"""
        username = os.environ.get('SOCKS_USERNAME', 'socks')
        password = os.environ.get('SOCKS_PASSWORD', 'change_me_now')

        # 同时测试域名与 IP，避免单一目标导致误判
        targets = [
            ('api.ipify.org', 443, True),
            ('ipv4.ip.sb', 443, True),
            ('1.1.1.1', 443, False),
        ]

        rep_map = {
            1: 'general SOCKS server failure',
            2: 'connection not allowed by ruleset',
            3: 'network unreachable',
            4: 'host unreachable',
            5: 'connection refused',
            6: 'TTL expired',
            7: 'command not supported',
            8: 'address type not supported',
        }

        def recv_exact(sock, n):
            data = b''
            while len(data) < n:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    break
                data += chunk
            return data

        errors = []
        for host, port, is_domain in targets:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(6)
            try:
                sock.connect(('127.0.0.1', 1080))

                # greeting: 支持 no-auth 和 username
                sock.sendall(b'\x05\x02\x00\x02')
                greeting_resp = recv_exact(sock, 2)
                if len(greeting_resp) != 2 or greeting_resp[0] != 5:
                    last_error = 'SOCKS5 greeting 响应异常'
                    continue

                method = greeting_resp[1]
                if method == 0xFF:
                    last_error = 'SOCKS5 不接受客户端认证方式'
                    continue

                if method == 0x02:
                    u = username.encode('utf-8')
                    p = password.encode('utf-8')
                    if len(u) > 255 or len(p) > 255:
                        last_error = 'SOCKS 认证凭据长度超过 255 字节'
                        continue

                    auth_req = bytes([1, len(u)]) + u + bytes([len(p)]) + p
                    sock.sendall(auth_req)
                    auth_resp = recv_exact(sock, 2)
                    if len(auth_resp) != 2 or auth_resp[1] != 0:
                        last_error = 'SOCKS5 用户名密码认证失败'
                        continue
                elif method != 0x00:
                    last_error = f'SOCKS5 返回不支持的认证方式: {method}'
                    continue

                if is_domain:
                    host_bytes = host.encode('idna')
                    if len(host_bytes) > 255:
                        errors.append(f'{host}:{port} 域名长度超过 255 字节')
                        continue
                    req = b'\x05\x01\x00\x03' + bytes([len(host_bytes)]) + host_bytes + port.to_bytes(2, 'big')
                else:
                    octets = bytes(int(part) for part in host.split('.'))
                    req = b'\x05\x01\x00\x01' + octets + port.to_bytes(2, 'big')
                sock.sendall(req)

                head = recv_exact(sock, 4)
                if len(head) != 4 or head[0] != 5:
                    last_error = f'{host}:{port} CONNECT 响应异常'
                    continue

                rep = head[1]
                atyp = head[3]
                if rep != 0:
                    rep_msg = rep_map.get(rep, f'unknown({rep})')
                    errors.append(f'{host}:{port} CONNECT 失败: {rep_msg}')
                    continue

                # 吃掉 BND.ADDR/BND.PORT
                if atyp == 1:
                    recv_exact(sock, 6)
                elif atyp == 4:
                    recv_exact(sock, 18)
                elif atyp == 3:
                    ln = recv_exact(sock, 1)
                    if len(ln) != 1:
                        errors.append(f'{host}:{port} 响应解析失败')
                        continue
                    recv_exact(sock, ln[0] + 2)

                return True, None
            except Exception as e:
                errors.append(f'{host}:{port} 探测异常: {e}')
            finally:
                try:
                    sock.close()
                except Exception:
                    pass

        if errors:
            return False, '；'.join(errors)
        return False, 'SOCKS5 可用性校验失败'
    
    def connect(self, server_ip, server_port=443):
        """连接到指定服务器"""
        try:
            self.last_error = None
            self.last_warning = None

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
            
            # 等待 VPN 会话建立（先确认隧道真的通了，再做 DHCP）
            if not self.interface_exists('vpn_vpn'):
                self.last_error = 'VPN 虚拟网卡 vpn_vpn 未建立，连接可能未成功'
                print(self.last_error)
                return False

            session_ok, session_status, session_detail = self.wait_for_session_connected(timeout=25)
            if not session_ok:
                if session_status == 'Retrying':
                    self.last_error = (
                        f'无法连接到 VPN 服务器 {server_ip}（Session: Retrying）。\n'
                        f'该节点可能离线、已满员，或网络不通。请尝试其他服务器。'
                    )
                elif session_status == 'Disconnected':
                    self.last_error = (
                        f'VPN 会话已断开（Session: Disconnected）。\n'
                        f'服务器 {server_ip} 拒绝连接或立即断开，请尝试其他服务器。'
                    )
                else:
                    self.last_error = (
                        f'VPN 会话未在规定时间内建立（Session: {session_status}，25s 超时）。\n'
                        f'服务器 {server_ip} 响应过慢或不稳定，请尝试其他服务器。'
                    )
                if session_detail:
                    self.last_error += f'\n---\n{session_detail}'
                print(self.last_error)
                return False

            # Session 已 Connected，开始 DHCP（带重试 & 诊断）
            dhcp_ok, dhcp_error = self.run_dhcp('vpn_vpn', attempts=3, per_attempt_timeout=10)

            vpn_ip = self.get_interface_ipv4('vpn_vpn')

            if (not dhcp_ok) or (not vpn_ip) or vpn_ip.startswith('169.254.'):
                stats = self.get_packet_stats()
                out_bcast = stats.get('out_bcast')
                in_bcast = stats.get('in_bcast')

                if out_bcast is not None and in_bcast is not None:
                    if out_bcast > 0 and in_bcast <= 4:
                        reason = (
                            '该节点 HUB 未响应 DHCP 请求（SecureNAT/DHCP 未配置或故障）'
                        )
                        suggestion = '请尝试其他服务器'
                    elif out_bcast == 0:
                        reason = '本地未发出任何广播包（容器 TUN/TAP 或 vpnclient 异常）'
                        suggestion = '请检查 /dev/net/tun 和容器特权权限'
                    else:
                        reason = '已收到部分广播但未完成 DHCP 握手'
                        suggestion = '可重试或更换服务器'
                    packet_info = f'广播包 {out_bcast} 出 / {in_bcast} 入'
                else:
                    reason = '无法获取隧道数据包统计'
                    suggestion = '请尝试其他服务器'
                    packet_info = None

                current_ip = vpn_ip or '无'
                diag_lines = [
                    f'VPN 隧道已建立（Session: Connected，Server: {server_ip}），但未能获取有效 IPv4 地址。',
                    f'当前接口地址: {current_ip}',
                ]
                if packet_info:
                    diag_lines.append(packet_info)
                diag_lines.append(f'原因判定: {reason}')
                diag_lines.append(f'建议: {suggestion}')
                if dhcp_error:
                    diag_lines.append(f'DHCP 详情: {dhcp_error}')

                self.last_error = '\n'.join(diag_lines)
                print(self.last_error)
                return False

            probe_ok, probe_error = self.probe_vpn_egress(vpn_ip)
            if not probe_ok:
                probe_strict = os.environ.get('REQUIRE_EGRESS_PROBE', '0').lower() in ('1', 'true', 'yes', 'on')
                msg = f'VPN 真实出网探测失败: {probe_error}'
                if probe_strict:
                    self.last_error = msg
                    print(self.last_error)
                    return False
                self.last_warning = msg
                print(f'警告: {msg}（已跳过严格校验，继续启动 SOCKS5）')
            
            # 重启 SOCKS5 代理（避免前台进程阻塞导致超时）
            socks_ok, socks_error = self.start_socks_proxy()
            if not socks_ok:
                self.last_error = f'SOCKS5 启动失败: {socks_error}'
                print(self.last_error)
                return False

            socks_ready, socks_ready_error = self.verify_socks_proxy()
            if not socks_ready:
                self.last_error = f'SOCKS5 可用性校验失败: {socks_ready_error}'
                print(self.last_error)
                return False
            
            self.current_connection = {
                'ip': server_ip,
                'port': server_port,
                'connected_at': datetime.now().isoformat()
            }
            self.save_config()
            self.last_error = None
            self.last_warning = None
            
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
    """获取服务器列表（默认返回缓存，force=1 时强制刷新）"""
    force = request.args.get('force', '').lower() in ('1', 'true', 'yes', 'on')

    if force or not vpn_manager.servers_cache:
        fresh = vpn_manager.get_vpngate_servers()
        if fresh:
            vpn_manager.servers_cache = fresh
            vpn_manager.servers_cache_at = datetime.now().isoformat()

    servers = vpn_manager.servers_cache or []
    return jsonify({
        'success': True,
        'servers': servers,
        'count': len(servers),
        'cached_at': vpn_manager.servers_cache_at,
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
