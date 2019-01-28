import socket
import sys

import paramiko

from chainup.log import logger


class Host(object):
    """Deployment roles"""
    CHAIN_VALIDATOR = 1
    CHAIN_NON_VALIDATOR = 1 << 1
    CHAIN_EXPLORER = 1 << 2
    OPS_MASTER = 1 << 3
    OPS_WORKER = 1 << 4
    CA_SERVER = 1 << 5
    NOT_INSTALLED = '(Not installed)'

    def __init__(self, address=None, username='root', password=None, sshport='22', note=None):
        self.address = address
        self.sshport = sshport
        self.username = username
        self.password = password
        self.note = note
        self._sftp = None
        self._client = None
        self.output = None
        self.is_valid = False
        self.info = {}
        self.role = 0

    def set_role(self, role):
        self.role = role

    def has_role(self, role):
        return self.role & role == role

    def try_connect(self):
        """Try to connect with host, and get information about OS/CPU/Mem etc.
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=self.address, username=self.username, password=self.password, port=int(self.sshport),
                        timeout=1)
            self._client = ssh
            self._sftp = ssh.open_sftp()
            self.info.clear()
            if self._check_os():
                self.is_valid = True
                self._get_info()
        except paramiko.BadAuthenticationType:
            logger.error('Bad authentication type: Host[%s].' % self.address)
            self.is_valid = False
            self.info.update({'Invalid': '主机不支持密码方式登录，请主机管理员进行设置。'})
        except paramiko.AuthenticationException:
            logger.error('Authentication failed: Host[%s].' % self.address)
            self.is_valid = False
            self.info.update({'Invalid': '认证失败，请检查用户名和密码是否正确。'})
        except paramiko.SSHException:
            logger.error('Connect to Host[%s] failed, SSH exception.' % self.address)
            self.is_valid = False
            self.info.update({'Invalid': '无法连接该主机。'})
        except socket.timeout:
            logger.error('Connect to Host[%s] timed out.' % self.address)
            self.is_valid = False
            self.info.update({'Invalid': '该主机连接超时。'})
        except socket.gaierror:
            logger.error('Connect to Host[%s] get addr info failed.' % self.address)
            self.is_valid = False
            self.info.update({'Invalid': '主机地址填写有误。'})
        # finally:
        #     ssh.close()

    def download(self, remote_path, local_path, callback=None):
        if self._sftp is None:
            self.try_connect()
        self._sftp.get(remote_path, local_path, callback=callback)

    def upload(self, local_path, remote_path, callback=None):
        if self._sftp is None:
            self.try_connect()
        self._sftp.put(local_path, remote_path, callback=callback)

    def unarchive(self, local_file_path, remote_dir_path, upload_callback=None):
        """unarchive uploads local file(local_file_path) to '/tmp' of remote host,
        and then extract this file to remote_dir_path.
        """
        file_name = local_file_path[local_file_path.rfind('\\') + 1:]
        self.upload(local_file_path, '/tmp/' + file_name, upload_callback)
        v_remote_dir = self.absolute_path(remote_dir_path)
        command = \
            'rm -rf ' + v_remote_dir + \
            ' && mkdir -p ' + v_remote_dir + \
            ' && tar xzvvf /tmp/' + file_name + ' -C ' + v_remote_dir + \
            ' && rm -f /tmp/' + file_name
        return self.exec_command_tail(command)

    def absolute_path(self, path):
        if path.startswith('~'):
            if self.username == 'root':
                return path.replace('~', '/root')
            else:
                return path.replace('~', '/home/%s' % self.username)
        return path

    def exec_command(self, command):
        if self._client is None:
            self.try_connect()
        stdin, stdout, stderr = self._client.exec_command(command, timeout=300, get_pty=True)
        stdin.close()
        v_exit_code = stdout.channel.recv_exit_status()
        logger.debug('exec_command: %s, exit %d.' % (command, v_exit_code))
        return v_exit_code, stdout

    def exec_command_tail(self, command):
        if self._client is None:
            self.try_connect()
        stdin, stdout, stderr = self._client.exec_command(command, timeout=300, get_pty=True)
        logger.debug('exec_command_tail: %s.' % command)
        stdin.close()
        return stdout

    def _check_os(self):
        stdin, stdout, stderr = self._client.exec_command('cat /etc/centos-release', get_pty=True)
        result = stdout.readline().strip()
        if result.find('CentOS Linux release 7') > -1:
            self.info.update({'OS': result.replace('Linux release ', '')})
            return True
        else:
            self.is_valid = False
            self.info.update({'Invalid': '请使用CentOS7系统'})
            return False

    # def check_port_accessible(self, port=None):
    #     sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #     sk.settimeout(3)
    #     try:
    #         if port is None:
    #             sk.connect((self.address, self.sshport))
    #             print(self.sshport)
    #         else:
    #             sk.connect((self.address, port))
    #             print(port)
    #         return True
    #     except Exception:
    #         return False
    #     finally:
    #         sk.close()

    def _get_info(self):
        self._get_hostname()
        self._check_os()
        self._get_host_cpu()
        self._get_host_mem()
        self._get_host_docker_info()

    def host_info_str(self):
        host_info = ''
        for k, v in self.info.items():
            host_info += '%10s : %s\n' % (k, v)
        host_info = host_info[0:-1]
        return host_info

    def _get_host_mem(self):
        stdin, stdout, stderr = self._client.exec_command('cat /proc/meminfo')
        for line in stdout.readlines():
            if line.startswith('MemTotal'):
                mem = int(line.split()[1].strip())
                mem = '%.f' % (mem / 1024.0) + ' MB'
                self.info.update({'Memory': mem})
                break

    def _get_host_cpu(self):
        cpu_model = 0
        cpu_num = 0
        stdin, stdout, stderr = self._client.exec_command('cat /proc/cpuinfo')
        for line in stdout.readlines():
            if line.startswith('processor'):
                cpu_num += 1
            if line.startswith('model name'):
                cpu_model = line.split(':')[1].strip().split()
                cpu_model = cpu_model[0] + ' ' + cpu_model[2] + ' ' + cpu_model[-1]
            if line == '':
                break
        self.info.update({'CPU': '%s x %s' % (cpu_model, cpu_num)})

    def _get_host_docker_info(self):
        stdin, stdout, stderr = self._client.exec_command('docker version')
        for line in stdout.readlines():
            if line.startswith('  Version:'):
                docker_version = line.split(':')[1].strip()
                self.info.update({'Docker': docker_version})
                return
        self.info.update({'Docker': Host.NOT_INSTALLED})

    def _get_hostname(self):
        stdin, stdout, stderr = self._client.exec_command('hostname')
        self.info.update({'Hostname': stdout.readline().strip()})

    def get_description(self):
        v_host_desc = 'new-host'
        if self.address != '':
            v_host_desc = self.address
        if self.note != '':
            v_host_desc += '(' + self.note + ')'
        return v_host_desc

    def close(self):
        if self._sftp:
            self._sftp.close()
        if self._client:
            self._client.close()


def progress_info(transferred, toBeTransferred):
    sys.stdout.write('\r')
    sys.stdout.write("Transferred: %10.2fkB/%10.2fkB" % (transferred / 1024, toBeTransferred / 1024))
    sys.stdout.flush()


if __name__ == '__main__':
    host = Host('10.1.1.29', 'root', 'kk', '22', 'test')
    # host.try_connect()
    # filename = OfflineResources.res_docker_rpm[OfflineResources.res_docker_rpm.rfind('\\') + 1:]
    # print(filename)
    # host.upload(OfflineResources.res_docker_rpm, '/tmp/' + filename)
    # host.upload('D:\ChainUp\LICENSE', '/root/')
    # host.upload('D:\Workspace\git\pyqt\chainup\LICENSE', '/root/test')
    # print('host  >>>')
    # print(host.host_info_str())
    # host.close()
    # host1 = copy.copy(host)
    # host1.info = copy.copy(host.info)
    # host1.info = {}
    # host1.address = '10.1.1.34'
    # host1.try_connect()
    # print('host1 >>>')
    # print(host1.host_info_str())
    # print('host  >>>')
    # print(host.host_info_str())
    # host.upload('D:\\ChainUp\\rpm_ansible.tar.gz', '/tmp/rpm_ansible.tar.gz', progress_info)
    output = host.unarchive('D:\\ChainUp\\rpm_sshpass.tar.gz', '/tmp/rpm_sshpass', progress_info)
    # result, output = host.exec_command('which ansible-playbook')
    print(output.readlines())
    # output.close()
    # if result != 0:
    #     exit_code, remote_dir = self.unarchive('D:\ChainUp\playbooks.tar.gz', '~')
    #     print(remote_dir)
    #     print(exit_code)

    # print(type(stdout))
    # print(isinstance(stdout, paramiko.channel.ChannelFile))
    # result, output = host.exec_command('ls /root')
    # print(output.readlines())
    # print(type(output))
    # print(output)
    # result = 'aaa'
    # print(isinstance(result, str))
    # for line in stdout.readlines():
    #     print(line, end='')
    # host.download('/root/test', "E:\license.txt")
    # host.set_role(0)
    # print(host.has_role(Host.OPS_MASTER))
    # print(host.has_role(Host.CHAIN_EXPLORER))
    # print(host.has_role(Host.CHAIN_VALIDATOR))
    # print(host.has_role(Host.CHAIN_NON_VALIDATOR))
    # host.check_port_accessible(80)
    host.close()
