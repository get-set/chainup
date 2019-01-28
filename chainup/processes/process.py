from PyQt5.QtCore import QRunnable
from PyQt5.QtGui import QPixmap

from chainup.deploy_schema import DeploySchema
from chainup.log import logger
from chainup.ui.singles import SignalsForThreads
from chainup.utils import Utils


class Process(QRunnable):
    """Checking processes and deployment processes.
    """
    STATUS_NOT_STARTED = 0
    STATUS_CHECKING = 1
    STATUS_PASSED = 2
    STATUS_FAILED = 3

    TYPE_CHECKING = "checking"
    TYPE_DEPLOYMENT = "deployment"

    deploy_schema = None
    all_stopped = False
    progress_value = 0
    job_type = TYPE_CHECKING
    ui = None

    def __init__(self, name, progress_weight=20):
        super().__init__()
        self.name = name
        self.status = Process.STATUS_NOT_STARTED
        self.status_widget = None
        self.progress_weight = progress_weight
        self.signals = SignalsForThreads()

    def set_status(self, status):
        self.status = status
        if not self.status_widget:
            return
        if status == Process.STATUS_NOT_STARTED:
            self.status_widget.setPixmap(QPixmap(":/icons/images/notyet.png"))
            self.status_widget.parent().setStyleSheet("border-color:gray")
        elif status == Process.STATUS_CHECKING:
            self.status_widget.setPixmap(QPixmap(":/icons/images/checking.png"))
            self.status_widget.parent().setStyleSheet("border-color:#F4EA2A")
        elif status == Process.STATUS_PASSED:
            self.status_widget.setPixmap(QPixmap(":/icons/images/ok.png"))
            self.status_widget.parent().setStyleSheet("border-color:#1AFA29")
        elif status == Process.STATUS_FAILED:
            self.status_widget.setPixmap(QPixmap(":/icons/images/no.png"))
            self.status_widget.parent().setStyleSheet("border-color:#D81E06")

    def run(self):
        if Process.all_stopped:
            return
        self._log_msg('==========' + Utils.time_stamp() + ' 开始' + self.name + '==========')
        self.set_status(Process.STATUS_CHECKING)
        self._run()
        if self.status == Process.STATUS_CHECKING:
            self.set_status(Process.STATUS_PASSED)

    def _run(self):
        pass

    def _log_msg(self, msg, passed=True):
        self.signals.log_append.emit(msg.strip())
        if passed:
            logger.debug(msg.strip())
        else:
            logger.error(msg.strip())

    def _log_stdout(self, stdout, passed=True):
        for line in iter(stdout.readline, ""):
            self.signals.log_append.emit("| " + line.strip())
            if passed:
                logger.debug(line.strip())
            else:
                logger.error(line.strip())

    def _summary(self, msg, passed=True):
        self.signals.summary_add.emit(passed, msg)

    def _exec(self, command_desc, host, command):
        output = host.exec_command_tail(command)
        self._log_msg('{%s} %s >>' % (host.address, command_desc))
        # self._log_msg('')
        self._log_stdout(output)
        exit_code = output.channel.recv_exit_status()

        if exit_code == 0:
            self._summary('{%s} %s成功' % (host.address, command_desc))
        else:
            self._summary('{%s} %s失败' % (host.address, command_desc), False)
            self._process_failed()
        output.close()

    def _upload_extract(self, src_desc, local_src, host, remote_dest):
        self._log_msg('{%s} 正在上传%s >>>' % (host.address, src_desc))
        self._log_msg('')
        output = host.unarchive(local_src, remote_dest, self._upload_progress)
        self._log_msg('{%s} 正在解压%s' % (host.address, src_desc))
        self._log_stdout(output)
        exit_code = output.channel.recv_exit_status()

        if exit_code != 0:
            self._log_msg('{%s} 解压%s失败' % (host.address, src_desc))
            self._process_failed()
        else:
            self._summary('{%s} 上传并解压%s成功' % (host.address, src_desc))
            self._log_msg('{%s} 解压%s成功' % (host.address, src_desc))

    def _upload_progress(self, transferred, to_be_transferred):
        self.signals.log_overwrite_last_line.emit(
            '| 已上传%.2fMB/%.2fMB(%.1f%%)' % (transferred / 1048576, to_be_transferred / 1048576,
                                            transferred * 100 / to_be_transferred))

    def _get_first_ops_host(self):
        v_host = sorted(self.deploy_schema.ops_master.keys())[0]
        return self.deploy_schema.ops_master[v_host]

    def _get_one_validator_address(self):
        return sorted(self.deploy_schema.chain_validators.keys())[0]

    def _run_ansible_playbook(self, playbook):
        if Process.all_stopped:
            return
        host = self._get_first_ops_host()
        self._exec(self.name, host,
                   'cd %s && ansible-playbook %s.yml' % (host.absolute_path(DeploySchema.PLAYBOOKS_DIR), playbook))

    def _progress_forward(self, delta):
        delta_value = round(delta * self.progress_weight / 100)
        if Process.progress_value + delta_value < 100:
            Process.progress_value = Process.progress_value + delta_value
        else:
            Process.progress_value = 99
        self.signals.progress_value_change.emit(Process.progress_value)

    def _process_failed(self):
        Process.all_stopped = True
        self.set_status(Process.STATUS_FAILED)
        self.signals.finished.emit()
