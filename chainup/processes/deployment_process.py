from chainup.processes.process import Process


class DeployChain(Process):
    def __init__(self):
        Process.__init__(self, '部署链节点', 50)

    def _run(self):
        self._run_ansible_playbook("deploy_chain")
        self._progress_forward(100)


class DeployOps(Process):
    def __init__(self):
        Process.__init__(self, '部署运维平台', 25)

    def _run(self):
        self._run_ansible_playbook("deploy_monitor")
        self._progress_forward(100)


class DeployExplorer(Process):
    def __init__(self):
        Process.__init__(self, '部署链浏览器', 25)

    def _run(self):
        self._run_ansible_playbook("deploy_explorer")
        self._progress_forward(100)
        self.signals.checking_finished.emit()

