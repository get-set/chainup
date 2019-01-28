import time

from chainup.deploy_schema import DeploySchema
from chainup.settings import Settings
from chainup.processes.process import Process


class PreparePlaybooks(Process):
    def __init__(self):
        Process.__init__(self, '准备playbooks', 30)

    def _run(self):
        if not self._check_playbooks_exist():
            self._extract_playbooks()
        self._generate_inventory()
        self._update_groupvars()

    def _check_playbooks_exist(self):
        if Process.all_stopped:
            return
        host = self._get_first_ops_host()
        exit_code, output = host.exec_command('ls ' + host.absolute_path(DeploySchema.PLAYBOOKS_DIR) + ' &> /dev/null')
        output.close()
        if exit_code == 0:
            self._summary('{%s} playbooks已存在' % host.address)
            self._progress_forward(80)
        return exit_code == 0

    def _extract_playbooks(self):
        if Process.all_stopped:
            return
        host = self._get_first_ops_host()
        self._upload_extract('playbooks', Settings.res_playbooks, host, DeploySchema.PLAYBOOKS_DIR)
        self._progress_forward(80)

    def _generate_inventory(self):
        if Process.all_stopped:
            return
        index = 0
        host = self._get_first_ops_host()
        inventory_file = host.absolute_path(DeploySchema.PLAYBOOKS_DIR + '/trustchain-nodes')
        command = 'echo \"[validators]\" > ' + inventory_file
        for (k, host) in Process.deploy_schema.chain_validators.items():
            command = command + \
                      ' && echo \"tcnode%d ansible_ssh_host=%s ansible_ssh_user=%s ansible_ssh_port=%s ansible_ssh_pass=%s\" >> %s' % (
                          index, host.address, host.username, host.sshport, host.password, inventory_file)
            index += 1

        command = command + ' && echo -e \"\\n[nonvalidators]\" >> ' + inventory_file
        for (k, host) in Process.deploy_schema.chain_non_validators.items():
            command = command + \
                      ' && echo \"tcnode%d ansible_ssh_host=%s ansible_ssh_user=%s ansible_ssh_port=%s ansible_ssh_pass=%s\" >> %s' % (
                          index, host.address, host.username, host.sshport, host.password, inventory_file)
            index += 1

        command = command + ' && echo -e \"\\n[explorer]\" >> ' + inventory_file
        for (k, host) in Process.deploy_schema.chain_explorers.items():
            command = command + \
                      ' && echo \"%s ansible_ssh_host=%s ansible_ssh_user=%s ansible_ssh_port=%s ansible_ssh_pass=%s\" >> %s' % (
                          host.note, host.address, host.username, host.sshport, host.password, inventory_file)

        command = command + ' && echo -e \"\\n[ops-master]\" >> ' + inventory_file
        for (k, host) in Process.deploy_schema.ops_master.items():
            command = command + \
                      ' && echo \"%s ansible_ssh_host=%s ansible_ssh_user=%s ansible_ssh_port=%s ansible_ssh_pass=%s\" >> %s' % (
                          host.note, host.address, host.username, host.sshport, host.password, inventory_file)

        command = command + ' && echo -e \"\\n[ops-worker]\" >> ' + inventory_file
        for (k, host) in Process.deploy_schema.ops_workers.items():
            command = command + \
                      ' && echo \"%s ansible_ssh_host=%s ansible_ssh_user=%s ansible_ssh_port=%s ansible_ssh_pass=%s\" >> %s' % (
                          host.note, host.address, host.username, host.sshport, host.password, inventory_file)

        command = command + ' && echo -e \"\\n[ca-server]\" >> ' + inventory_file
        for (k, host) in Process.deploy_schema.ca_servers.items():
            command = command + \
                      ' && echo \"%s ansible_ssh_host=%s ansible_ssh_user=%s ansible_ssh_port=%s ansible_ssh_pass=%s\" >> %s' % (
                          host.note, host.address, host.username, host.sshport, host.password, inventory_file)

        command = command + ' && echo -e \"\\n[ops:children]\\nops-master\\nops-worker\\n\\n[chainnodes:children]\\nvalidators\\nnonvalidators\" >> ' + inventory_file

        self._exec('生成inventory文件', host, command)
        self._progress_forward(10)

    def _update_groupvars(self):
        if Process.all_stopped:
            return
        host = self._get_first_ops_host()
        group_var_file = host.absolute_path(DeploySchema.PLAYBOOKS_DIR + '/group_vars/all')
        command = \
            'sed -i \'/^peer_port: /c\\peer_port: "' + self.deploy_schema.chain_peer_port + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^rpc_port: /c\\rpc_port: "' + self.deploy_schema.chain_rpc_port + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^proxy_app: /c\\proxy_app: "' + self.deploy_schema.chain_proxy_app + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^chain_home : /c\\chain_home : "' + host.absolute_path(
                self.deploy_schema.chain_home) + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^es_host: /c\\es_host: "' + host.address + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^es_port: /c\\es_port: "' + self.deploy_schema.ops_es_port + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^monitor_home : /c\\monitor_home : "' + host.absolute_path(
                self.deploy_schema.ops_monitor_home) + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^kibana_port: /c\\kibana_port: "' + self.deploy_schema.ops_kibana_port + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^explorer_home : /c\\explorer_home : "' + host.absolute_path(
                self.deploy_schema.chain_explorer_home) + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^explorer_port: /c\\explorer_port: "' + self.deploy_schema.chain_explorer_port + '"\' ' + group_var_file + ' && ' + \
            'sed -i \'/^explorer_connected_host: /c\\explorer_connect_host: "' + self._get_one_validator_address() + '"\' ' + group_var_file + ' && '
        if self.deploy_schema.chain_crypto_sm:
            command = command + 'sed -i \'/^crypto_with_sm2: /c\\crypto_with_sm2: "true"\' ' + group_var_file
        else:
            command = command + 'sed -i \'/^crypto_with_sm2: /c\\crypto_with_sm2: "false"\' ' + group_var_file

        self._exec('更新group_vars/all文件', host, command)
        self._progress_forward(10)


class InstallAnsible(Process):
    def __init__(self):
        Process.__init__(self, '安装ansible', 15)

    def _run(self):
        if not self._check_sshpass_installed():
            self._install_sshpass()
        if not self._check_ansible_installed():
            self._install_ansible()
        self._ssh_copyid()

    def _check_ansible_installed(self):
        if Process.all_stopped:
            return
        host = self._get_first_ops_host()
        exit_code, output = host.exec_command('which ansible-playbook')
        output.close()
        if exit_code == 0:
            self._summary('{%s} ansible已安装' % host.address)
            self._progress_forward(60)
        return exit_code == 0

    def _install_ansible(self):
        if Process.all_stopped:
            return
        # Only one host in ops_master
        host = self._get_first_ops_host()
        # extract rpm_ansible.tar.gz first
        self._upload_extract('ansible', Settings.res_rpm_ansible, host, '/tmp/rpm_ansible')

        # and then install ansible
        command = \
            'yum install -y /tmp/rpm_ansible/*.rpm && ' + \
            'rm -rf /tmp/rpm_ansible'
        self._exec('ansible安装', host, command)
        self._progress_forward(60)

    def _check_sshpass_installed(self):
        if Process.all_stopped:
            return
        host = self._get_first_ops_host()
        exit_code, output = host.exec_command('which sshpass')
        output.close()
        if exit_code == 0:
            self._log_msg('{%s} sshpass已安装' % host.address)
            self._progress_forward(30)
        return exit_code == 0

    def _install_sshpass(self):
        if Process.all_stopped:
            return
        host = self._get_first_ops_host()
        self._upload_extract('sshpass', Settings.res_rpm_sshpass, host, '/tmp/rpm_sshpass')

        # and then install sshpass
        command = \
            'yum install -y /tmp/rpm_sshpass/*.rpm && ' + \
            'rm -rf /tmp/rpm_sshpass'
        self._exec('sshpass安装', host, command)
        self._progress_forward(30)

    def _ssh_copyid(self):
        if Process.all_stopped:
            return
        host = self._get_first_ops_host()
        ssh_copyid_script = host.absolute_path(DeploySchema.PLAYBOOKS_DIR + '/ssh-copy-id-nodes.sh')
        command = 'bash ' + ssh_copyid_script
        self._exec('SSH密钥登录配置', host, command)
        self._progress_forward(10)


class InstallDocker(Process):
    def __init__(self):
        Process.__init__(self, '安装Docker', 10)

    def _run(self):
        self._run_ansible_playbook("prep_docker")
        self._progress_forward(100)


class CheckComputing(Process):
    def __init__(self):
        Process.__init__(self, '检查系统资源', 10)

    def _run(self):
        self._run_ansible_playbook("check_computing")
        self._progress_forward(100)


class CheckNetwork(Process):
    def __init__(self):
        Process.__init__(self, '检查网络资源', 25)

    def _run(self):
        self._run_ansible_playbook("check_network")
        self._progress_forward(100)


class CheckStorage(Process):
    def __init__(self):
        Process.__init__(self, '检查存储资源', 10)

    def _run(self):
        self._run_ansible_playbook("check_storage")
        self._progress_forward(100)
        time.sleep(1)
        self.signals.finished.emit()
