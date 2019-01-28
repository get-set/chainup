# -*- coding: utf-8 -*-
import copy

from PyQt5.QtCore import Qt, pyqtSlot, QSize, QCoreApplication, QThreadPool
from PyQt5.QtGui import QIcon, QPixmap, QTextCursor
from PyQt5.QtWidgets import (QMainWindow, QListWidgetItem, QMessageBox, QFrame, QHBoxLayout, QLabel, QSizePolicy,
                             QSpacerItem, QApplication)

from chainup.deploy_schema import HostDeploySchema
from chainup.host import Host
from chainup.log import logger
from chainup.page import Pages
from chainup.processes.checking_process import *
from chainup.processes.deployment_process import *
from chainup.ui.threads import HostInfoUpdater
from chainup.ui.ui_main_frame import Ui_MainWindow
from chainup.utils import Utils


class MainWindow(QMainWindow, Ui_MainWindow):
    """Create the main window that stores all of the widgets necessary for the application."""

    def __init__(self, *args, **kwargs):
        """Initialize the components of the main window."""
        super().__init__(*args, **kwargs)

        self._translate = QCoreApplication.translate

        # Setup ui defined in ui_main_frame.py (which is generated by qt-designer and pyuic).
        self.setupUi(self)

        # Used to record current step and the step that has reached.
        self._current_page = Pages.START
        self._reached_page = Pages.START

        # QThreadPool object, used to run job in a synchronized way
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(1)

        # Initialize navigator and main content, begin from "开始"
        self._ensure_navigator_accessibility()
        self.nav_menu.setCurrentRow(-1)
        self.nav_process.setCurrentRow(Pages.START)
        self.stacked_pages.setCurrentIndex(Pages.START)
        self._ensure_btn_prev_next_state()

        """Navigator on the left"""
        # Connect navigator events with slots.
        self.nav_process.currentRowChanged.connect(self.slot_nav_process_current_row_changed)
        self.nav_menu.currentRowChanged.connect(self.slot_nav_menu_current_row_changed)

        """Main content frame on the right"""
        # Connect events of main content pages with slots.
        self.stacked_pages.currentChanged.connect(self.slot_stacked_pages_changed)
        # Connect prev & next button events with its slots.
        self.btn_prev.clicked.connect(self.slot_btn_prev_clicked)
        self.btn_next.clicked.connect(self.slot_btn_next_clicked)

        """PAGE 0: start"""
        # Only words.

        """PAGE 1: deployment schema"""
        self.radio_schema_test_single.clicked.connect(self.slot_page1_deploy_schema_selected)
        self.radio_schema_test_four.clicked.connect(self.slot_page1_deploy_schema_selected)
        self.radio_schema_prod_four.clicked.connect(self.slot_page1_deploy_schema_selected)
        self.radio_schema_custom.clicked.connect(self.slot_page1_deploy_schema_selected)

        """PAGE 2: resource information"""
        # Variables:
        # _current_host reflects "主机信息" group box
        self._current_host = Host()
        # _deploy_schema collected from page-2: deployment schema
        self._deploy_schema = None

        # Slots:
        # self.hosts_list.setCurrentRow(0)
        self.hosts_list.itemClicked.connect(self.slot_page2_hosts_list_item_clicked)
        self.btn_host_add_save.clicked.connect(self.slot_page2_host_add_save)
        self.btn_host_delete.clicked.connect(self.slot_page2_host_delete)
        # Try to connect when address/sshport/username/password changed.
        self.host_address.editingFinished.connect(self.slot_page2_host_connection_changed)
        self.host_username.editingFinished.connect(self.slot_page2_host_connection_changed)
        self.host_password.editingFinished.connect(self.slot_page2_host_connection_changed)
        self.host_sshport.editingFinished.connect(self.slot_page2_host_connection_changed)
        self.host_note.editingFinished.connect(self.slot_page2_host_info_changed)
        self.host_deploy_validator.stateChanged.connect(self.slot_page2_host_info_changed)
        self.host_deploy_nonvalidator.stateChanged.connect(self.slot_page2_host_info_changed)
        self.host_deploy_ops.stateChanged.connect(self.slot_page2_host_info_changed)
        self.host_deploy_explorer.stateChanged.connect(self.slot_page2_host_info_changed)
        self.host_deploy_caserver.stateChanged.connect(self.slot_page2_host_info_changed)

        """PAGE 3: deployment configuration"""
        # Variables:

        # Update configurations when changed
        self.chain_peer_port.editingFinished.connect(self.slot_page3_config_changed)
        self.chain_rpc_port.editingFinished.connect(self.slot_page3_config_changed)
        self.chain_proxy_app.editingFinished.connect(self.slot_page3_config_changed)
        self.chain_home.editingFinished.connect(self.slot_page3_config_changed)
        self.chain_crypto_sm.stateChanged.connect(self.slot_page3_config_changed)
        self.ops_es_port.editingFinished.connect(self.slot_page3_config_changed)
        self.ops_monitor_home.editingFinished.connect(self.slot_page3_config_changed)
        self.ops_kibana_port.editingFinished.connect(self.slot_page3_config_changed)
        self.explorer_port.editingFinished.connect(self.slot_page3_config_changed)

        """PAGE 4: deployment check"""
        # Variables:
        Process.ui = self
        self._page4_inited = False
        self._checking_jobs = [PreparePlaybooks(), InstallAnsible(), InstallDocker(), CheckComputing(), CheckNetwork(),
                               CheckStorage()]
        # Slots
        self.btn_check_start.clicked.connect(self.slot_page4_check_start)

        """PAGE 5: deployment"""
        # Variables:
        Process.ui = self
        self._page5_inited = False
        self._deployment_jobs = [DeployOps(), DeployChain(), DeployExplorer()]
        # Slots
        self.btn_deployment_start.clicked.connect(self.slot_page5_deployment_start)

    """ The following methods handles navigator on the left. """

    @pyqtSlot(int)
    def slot_nav_process_current_row_changed(self, row):
        """Triggered when change selected deployment step on the left-top"""
        logger.debug('[slot] nav_process_current_row_changed triggered')
        page = row
        if page < 0 or page > self._reached_page:
            return
        self._current_page = page
        self.nav_menu.setCurrentRow(-1)
        self.stacked_pages.setCurrentIndex(page)
        self._ensure_navigator_accessibility()

    @pyqtSlot(int)
    def slot_nav_menu_current_row_changed(self, row):
        """Triggered when change selected menu item on the left-bottom"""
        logger.debug('[slot] nav_menu_current_row_changed triggered')
        page = row + Pages.SETTINGS
        if page == Pages.CLOSE:
            self.close()
            return
        self.nav_process.setCurrentRow(-1)
        self.stacked_pages.setCurrentIndex(page)
        # self._ensure_buttons_availability()

    def _ensure_navigator_accessibility(self):
        for i in range(0, self._reached_page + 1):
            self.nav_process.item(i).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

    """ The following methods handles main content frame on the right. """

    @pyqtSlot(int)
    def slot_stacked_pages_changed(self, index):
        logger.debug('[slot] stacked_pages_changed triggered')
        if index == Pages.SCHEMA:
            self.slot_page1_deploy_schema_selected()
        if index == Pages.RESOURCES:
            pass
        if index == Pages.CONFIG:
            self._init_config_page()
        if index == Pages.CHECK:
            if not self._page4_inited:
                self._init_page4_checking()
        if index == Pages.DEPLOY:
            if not self._page5_inited:
                self._init_page5_deployment()
        self._ensure_btn_prev_next_state()

    def _ensure_btn_prev_next_state(self):
        """Called when page changed, to initialize prev/next button's state."""
        page_num = self.stacked_pages.currentIndex()
        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.btn_prev.setEnabled(True)
        self.btn_next.setEnabled(True)
        # page 0
        if page_num == Pages.START:
            self.btn_prev.setVisible(False)
        # page 1
        elif page_num == Pages.SCHEMA:
            pass
        # page 2
        elif page_num == Pages.RESOURCES:
            if not self._deploy_schema.has_meet_schema():
                self.btn_next.setEnabled(False)
            if self.hosts_list.count() > 0:
                self.slot_page2_hosts_list_item_clicked()
        # page 3
        elif page_num == Pages.CONFIG:
            pass
        # page 4
        elif page_num == Pages.CHECK:
            self.btn_next.setEnabled(self._has_all_jobs_passed(self._checking_jobs))
            self.btn_next.setEnabled(True)
        # page 5
        elif page_num == Pages.DEPLOY:
            self.btn_next.setEnabled(self._has_all_jobs_passed(self._deployment_jobs))
        elif page_num >= Pages.FINISH:
            self.btn_prev.setVisible(False)
            self.btn_next.setVisible(False)

    @pyqtSlot()
    def slot_btn_prev_clicked(self):
        """Triggered when prev button clicked."""
        logger.debug('[slot] btn_prev_clicked triggered')
        if self._current_page > Pages.START:
            self._current_page -= 1
            self.nav_process.setCurrentRow(self._current_page)
            # self.stacked_pages.setCurrentIndex(self.current_page)

    @pyqtSlot()
    def slot_btn_next_clicked(self):
        """Triggered when next button clicked."""
        logger.debug('[slot] btn_next_clicked triggered')
        # handles current page
        if self._current_page == Pages.SCHEMA:
            self._handle_page_schema()
            self._update_host_checkbox_state()
        if self._current_page == Pages.RESOURCES:
            if not self._deploy_schema.has_meet_schema():
                QMessageBox.warning(self, '注意', '主机部署内容的设置与上一页设置的部署计划不符，请检查。')
                return

        # handles next page
        if self._current_page < Pages.FINISH:
            self._current_page += 1
            if self._current_page > self._reached_page:
                self._reached_page += 1
                # self._ensure_navigator_accessibility()
            self.nav_process.setCurrentRow(self._current_page)
            # self.stacked_pages.setCurrentIndex(self.current_page)

    """Handlers for page 1: deployment schema"""

    @pyqtSlot()
    def slot_page1_deploy_schema_selected(self):
        """Triggered when choose different deploy schema"""
        logger.debug('[slot] deploy_schema_selected triggered')
        enabled = self.radio_schema_custom.isChecked()
        self.custom_num_validator.setEnabled(enabled)
        self.custom_num_non_validator.setEnabled(enabled)
        self.custom_num_ops.setEnabled(enabled)
        self.custom_num_explorer.setEnabled(enabled)
        self.custom_num_caserver.setEnabled(enabled)

    def _handle_page_schema(self):
        """Called before turn to page RESOURCES (refresh _target_deployment)"""
        logger.debug('[slot] _handle_page_schema triggered')
        if self.radio_res_type_host.isChecked():
            if type(self._deploy_schema) != HostDeploySchema:
                self._deploy_schema = HostDeploySchema()

        if self.radio_schema_test_single.isChecked():
            self._deploy_schema.schema = DeploySchema.PRESET_TEST_SINGLE
            self._deploy_schema.preset_test_single()
        elif self.radio_schema_test_four.isChecked():
            self._deploy_schema.schema = DeploySchema.PRESET_TEST_FOUR
            self._deploy_schema.preset_test_four()
        elif self.radio_schema_prod_four.isChecked():
            self._deploy_schema.schema = DeploySchema.PRESET_PROD_FOUR
            self._deploy_schema.preset_prod_four()
        elif self.radio_schema_custom.isChecked():
            self._deploy_schema.schema = DeploySchema.CUSTOM_SCHEMA
            self._deploy_schema.num_chain_validators = self.custom_num_validator.value()
            self._deploy_schema.num_chain_non_validators = self.custom_num_non_validator.value()
            self._deploy_schema.num_ops = self.custom_num_ops.value()
            self._deploy_schema.num_chain_explorer = self.custom_num_explorer.value()
            self._deploy_schema.num_caserver = self.custom_num_caserver.value()

    """Handlers for page 2: resources information """

    @pyqtSlot()
    def slot_page2_host_connection_changed(self):
        """Triggered when address/sshport/username/password changed(lost focus actually)"""
        logger.debug('[slot] host_connection_changed triggered')
        if self.host_address.text().strip() != "" \
                and self.host_sshport.text().strip() != "" \
                and self.host_username.text().strip() != "" \
                and self.host_password.text().strip() != "" \
                and (self.host_address.text().strip() != self._current_host.address
                     or self.host_sshport.text().strip() != self._current_host.sshport
                     or self.host_username.text().strip() != self._current_host.username
                     or self.host_password.text().strip() != self._current_host.password):
            # try to connect host on a separate thread.
            # if self._thread is None:
            self._update_host_object_from_ui()
            host_info_update_thread = HostInfoUpdater(self._current_host)
            host_info_update_thread.signals.validate_finished.connect(self.host_info_validated)
            self._thread_pool.start(host_info_update_thread)
            logger.debug("%d active threads in thread pool." % self._thread_pool.activeThreadCount())
            self._current_host.info = {}
            # self._update_host_object_from_ui()

    @pyqtSlot()
    def host_info_validated(self):
        """Triggered by HostInfoUpdater thread."""
        logger.debug('[slot] host_info_validated triggered')
        self.host_info.setPlainText(self._current_host.host_info_str())
        # self._thread.quit()
        # self._thread = None
        if self._current_host.is_valid:
            self.btn_host_add_save.setEnabled(True)
            # self.hosts_list.setEnabled(True)
        else:
            self.btn_host_add_save.setEnabled(False)
            # self.hosts_list.setEnabled(False)

    @pyqtSlot()
    def slot_page2_host_info_changed(self):
        """Triggered when other host input field changed."""
        logger.debug('[slot] host_info_changed triggered')
        sender = self.sender()

        # not allowed to deploy validator and non-validator on the same host.
        if sender == self.host_deploy_validator and sender.isChecked():
            self.host_deploy_nonvalidator.setChecked(False)
        elif sender == self.host_deploy_nonvalidator and sender.isChecked():
            self.host_deploy_validator.setChecked(False)

        # self._update_host_object_from_ui()
        if self._current_host.is_valid:
            self.btn_host_add_save.setEnabled(True)

    def _fill_in_ui_from_host_object(self):
        """Called when choose different host (change hosts_list widget rows)."""
        self.host_address.setText(self._current_host.address)
        self.host_sshport.setText(self._current_host.sshport)
        self.host_username.setText(self._current_host.username)
        self.host_password.setText(self._current_host.password)
        self.host_note.setText(self._current_host.note)
        self.host_deploy_validator.setChecked(self._current_host.has_role(Host.CHAIN_VALIDATOR))
        self.host_deploy_nonvalidator.setChecked(self._current_host.has_role(Host.CHAIN_NON_VALIDATOR))
        self.host_deploy_ops.setChecked(self._current_host.has_role(Host.OPS_MASTER))
        self.host_deploy_caserver.setChecked(self._current_host.has_role(Host.CA_SERVER))
        self.host_deploy_explorer.setChecked(self._current_host.has_role(Host.CHAIN_EXPLORER))
        self.host_info.setPlainText(self._current_host.host_info_str())

    def _update_host_object_from_ui(self):
        """Update _current_host object from ui widget."""
        self._current_host.address = self.host_address.text().strip()
        self._current_host.sshport = self.host_sshport.text().strip()
        self._current_host.username = self.host_username.text().strip()
        self._current_host.password = self.host_password.text().strip()
        self._current_host.note = self.host_note.text().strip()
        v_host_role = 0
        if self.host_deploy_validator.isChecked():
            v_host_role |= Host.CHAIN_VALIDATOR
        if self.host_deploy_nonvalidator.isChecked():
            v_host_role |= Host.CHAIN_NON_VALIDATOR
        if self.host_deploy_ops.isChecked():
            v_host_role |= Host.OPS_MASTER
        if self.host_deploy_explorer.isChecked():
            v_host_role |= Host.CHAIN_EXPLORER
        if self.host_deploy_caserver.isChecked():
            v_host_role |= Host.CA_SERVER
        self._current_host.set_role(v_host_role)

    @pyqtSlot(QListWidgetItem)
    def slot_page2_hosts_list_item_clicked(self, item=None):
        """Triggered when change hosts_list widget rows"""
        logger.debug('[slot] hosts_list_item_clicked triggered')
        if item is None:
            if self.hosts_list.count() == 0:
                return
            else:
                item = self.hosts_list.currentItem()
        v_saved_host = self._deploy_schema.all_hosts.get(item.text().split('(')[0])
        if v_saved_host:
            self._current_host = copy.copy(v_saved_host)
            self._current_host.info = copy.copy(v_saved_host.info)
            logger.debug('fetch %s-Host[%s], with role %d' % (
                item.text().split('(')[0], self._current_host.address, self._current_host.role))
            self._fill_in_ui_from_host_object()
            self._update_host_checkbox_state(True)
            self.btn_host_add_save.setEnabled(False)

    @pyqtSlot()
    def slot_page2_host_add_save(self):
        """Triggered when 'add/save' button clicked."""
        logger.debug('[slot] host_add_save triggered')
        self._update_host_object_from_ui()

        v_saved_host = copy.copy(self._current_host)
        v_saved_host.info = copy.copy(self._current_host.info)
        # Add to background data model.
        self._deploy_schema.add_or_update_host(v_saved_host)
        logger.info('Host added/saved: Host[%s], with role %d' % (v_saved_host.address, self._current_host.role))
        logger.info(
            'Now hosts_list contains %d items: %s' % (
                self._deploy_schema.all_hosts.keys().__len__(), self._deploy_schema.all_hosts.keys()))
        logger.debug(v_saved_host.note)

        # If already exists, update it.
        v_is_address_exist = False
        for i in range(self.hosts_list.count()):
            if self.hosts_list.item(i).text().startswith(v_saved_host.address):
                v_is_address_exist = True
                self.hosts_list.setCurrentRow(i)
                self.hosts_list.item(i).setText(v_saved_host.get_description())

        # If not exists, create and save it.
        if not v_is_address_exist:
            new_item = QListWidgetItem(QIcon(":/icons/images/host_valid.png"), v_saved_host.get_description())
            self.hosts_list.addItem(new_item)
            self.hosts_list.setCurrentItem(new_item)
            self.host_address.setFocus()

        if not self._deploy_schema.has_meet_schema():
            self._update_host_checkbox_state(False)
            self.host_info.clear()
        self.btn_host_delete.setEnabled(True)
        self.btn_host_add_save.setEnabled(False)
        # self.btn_next.setEnabled(self._deploy_schema.has_meet_schema())
        if self._deploy_schema.has_meet_schema():
            self.btn_next.setEnabled(True)
            self.btn_next.setFocus()
        else:
            self.btn_next.setEnabled(False)

    @pyqtSlot()
    def slot_page2_host_delete(self):
        """Triggered when click 'delete' button."""
        logger.debug('[slot] host_delete triggered')
        v_selected_item = self.hosts_list.takeItem(self.hosts_list.currentRow())
        v_host_addr = v_selected_item.text().split('(')[0]
        self.hosts_list.removeItemWidget(v_selected_item)
        self._deploy_schema.remove_host(v_host_addr)
        logger.info('Host deleted: Host[%s]' % v_host_addr)
        logger.info(
            'Now hosts_list contains %d items: %s' % (
                self._deploy_schema.all_hosts.keys().__len__(), self._deploy_schema.all_hosts.keys()))
        if self.hosts_list.count() == 0:
            self.btn_host_delete.setEnabled(False)
        self._update_host_checkbox_state()
        self.btn_next.setEnabled(self._deploy_schema.has_meet_schema())

    def _update_host_checkbox_state(self, editable=False):
        self.host_address.setFocus()

        self.host_deploy_validator.setEnabled((editable and self.host_deploy_validator.isChecked())
                                              or not self._deploy_schema.has_enough_chain_validators())
        if not self.host_deploy_validator.isEnabled():
            self.host_deploy_validator.setChecked(False)

        self.host_deploy_nonvalidator.setEnabled((editable and self.host_deploy_nonvalidator.isChecked())
                                                 or not self._deploy_schema.has_enough_chain_non_validators())
        if not self.host_deploy_nonvalidator.isEnabled():
            self.host_deploy_nonvalidator.setChecked(False)

        self.host_deploy_explorer.setEnabled((editable and self.host_deploy_explorer.isChecked())
                                             or not self._deploy_schema.has_enough_chain_explorer())
        if not self.host_deploy_explorer.isEnabled():
            self.host_deploy_explorer.setChecked(False)

        self.host_deploy_ops.setEnabled((editable and self.host_deploy_ops.isChecked())
                                        or not self._deploy_schema.has_enough_ops())
        if not self.host_deploy_ops.isEnabled():
            self.host_deploy_ops.setChecked(False)

        self.host_deploy_caserver.setEnabled((editable and self.host_deploy_caserver.isChecked())
                                             or not self._deploy_schema.has_enough_ca_servers())
        if not self.host_deploy_caserver.isEnabled():
            self.host_deploy_caserver.setChecked(False)

    """Handlers for page 3: resources configuration"""

    def _init_config_page(self):
        """Initialize Page 3, especially hosts list on which to deploy each components."""
        self.chain_onhosts.clear()
        for (k, v) in self._deploy_schema.chain_validators.items():
            self.chain_onhosts.addItem(QListWidgetItem(QIcon(":/icons/images/host_valid.png"), str(k + '[V]')))
        for (k, v) in self._deploy_schema.chain_non_validators.items():
            self.chain_onhosts.addItem(QListWidgetItem(QIcon(":/icons/images/host_valid.png"), str(k + '[NV]')))
        self.explorer_onhosts.clear()
        for (k, v) in self._deploy_schema.chain_explorers.items():
            self.explorer_onhosts.addItem(QListWidgetItem(QIcon(":/icons/images/host_valid.png"), str(k)))
        self.ops_onhosts.clear()
        for (k, v) in self._deploy_schema.ops_master.items():
            self.ops_onhosts.addItem(QListWidgetItem(QIcon(":/icons/images/host_valid.png"), str(k + '[M]')))
        for (k, v) in self._deploy_schema.ops_workers.items():
            self.ops_onhosts.addItem(QListWidgetItem(QIcon(":/icons/images/host_valid.png"), str(k + '[W]')))
        self.caserver_onhosts.clear()
        for (k, v) in self._deploy_schema.ca_servers.items():
            self.caserver_onhosts.addItem(QListWidgetItem(QIcon(":/icons/images/host_valid.png"), str(k)))

    @pyqtSlot()
    def slot_page3_config_changed(self):
        logger.debug('[slot] slot_page3_config_changed triggered')
        if self.chain_peer_port.text().strip() == "" or \
                self.chain_rpc_port.text().strip() == "" or \
                self.chain_proxy_app.text().strip() == "" or \
                self.chain_home.text().strip() == "" or \
                self.ops_es_port.text().strip() == "" or \
                self.ops_monitor_home.text().strip() == "" or \
                self.ops_kibana_port.text().strip() == "" or \
                self.explorer_port.text().strip() == "":
            self.btn_next.setEnabled(False)
        else:
            self.btn_next.setEnabled(True)

        self._deploy_schema.chain_peer_port = self.chain_peer_port.text()
        self._deploy_schema.chain_rpc_port = self.chain_rpc_port.text()
        self._deploy_schema.chain_proxy_app = self.chain_proxy_app.text()
        self._deploy_schema.chain_home = self.chain_home.text()
        self._deploy_schema.chain_crypto_sm = self.chain_crypto_sm.isChecked()

        self._deploy_schema.ops_es_port = self.ops_es_port.text()
        self._deploy_schema.ops_monitor_home = self.ops_monitor_home.text()
        self._deploy_schema.ops_kibana_port = self.ops_kibana_port.text()

        self._deploy_schema.chain_explorer_port = self.explorer_port.text()

    """common util methods used by page4 and page5"""

    def _add_process_items(self, label_str, parent_widget):
        # v_check_item_frame = QFrame(self.page_4)
        v_check_item_frame = QFrame()
        v_check_item_frame.setFrameShape(QFrame.StyledPanel)
        v_check_item_frame.setFrameShadow(QFrame.Raised)
        v_check_item_frame_layout = QHBoxLayout(v_check_item_frame)
        v_check_item_label = QLabel(v_check_item_frame)
        v_check_item_frame_layout.addWidget(v_check_item_label)
        v_check_item_status = QLabel(v_check_item_frame)
        v_size_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        v_size_policy.setHorizontalStretch(0)
        v_size_policy.setVerticalStretch(0)
        v_size_policy.setHeightForWidth(v_check_item_status.sizePolicy().hasHeightForWidth())
        v_check_item_status.setSizePolicy(v_size_policy)
        v_check_item_status.setMaximumSize(QSize(20, 20))
        v_check_item_status.setText("")
        v_check_item_status.setPixmap(QPixmap(":/icons/images/notyet.png"))
        v_check_item_status.setScaledContents(True)
        v_check_item_status.setObjectName("result_check_deployment")
        v_check_item_frame_layout.addWidget(v_check_item_status)
        v_check_item_frame.setProperty("class", self._translate("MainWindow", "check"))
        v_check_item_label.setText(self._translate("MainWindow", label_str))
        parent_widget.addWidget(v_check_item_frame)
        return v_check_item_status

    @staticmethod
    def _has_all_jobs_passed(jobs):
        v_job_num = jobs.__len__()
        if v_job_num == 0:
            return False
        for i in range(v_job_num):
            if jobs[i].status != Process.STATUS_PASSED:
                return False
        return True

    @pyqtSlot(str)
    def slot_page4_page5_log_append(self, msg):
        QApplication.processEvents()
        if Process.job_type == Process.TYPE_CHECKING:
            if not msg.startswith('|'):
                self.checking_log.appendPlainText('')
            self.checking_log.appendPlainText(msg.strip())
        elif Process.job_type == Process.TYPE_DEPLOYMENT:
            if not msg.startswith('|'):
                self.deployment_log.appendPlainText('')
            self.deployment_log.appendPlainText(msg.strip())

    @pyqtSlot(str)
    def slot_page4_page5_log_overwrite_last_line(self, msg):
        QApplication.processEvents()
        if Process.job_type == Process.TYPE_CHECKING:
            tc = self.checking_log.textCursor()
        elif Process.job_type == Process.TYPE_DEPLOYMENT:
            tc = self.deployment_log.textCursor()
        tc.select(QTextCursor.LineUnderCursor)
        tc.removeSelectedText()
        tc.insertText(msg)

    @pyqtSlot(bool, str)
    def slot_page4_page5_summary_add(self, passed, msg):
        QApplication.processEvents()
        logger.debug('[slot] slot_page4_page5_summary_add triggered')
        if passed:
            new_item = QListWidgetItem(QIcon(":/icons/images/ok.png"), str(Utils.time_stamp() + msg))
        else:
            new_item = QListWidgetItem(QIcon(":/icons/images/no.png"), str(Utils.time_stamp() + msg))

        if Process.job_type == Process.TYPE_CHECKING:
            self.checking_summary.addItem(new_item)
        elif Process.job_type == Process.TYPE_DEPLOYMENT:
            self.deployment_summary.addItem(new_item)

    @pyqtSlot(int)
    def slot_page4_page5_progress_value_change(self, value):
        QApplication.processEvents()
        logger.debug('[slot] slot_page4_page5_progress_value_change triggered')
        if Process.job_type == Process.TYPE_CHECKING:
            self.check_progress.setValue(value)
        elif Process.job_type == Process.TYPE_DEPLOYMENT:
            self.deployment_progress.setValue(value)

    @pyqtSlot()
    def slot_page4_page5_finished(self):
        QApplication.processEvents()
        logger.debug('[slot] slot_page4_page5_finished triggered')
        if Process.job_type == Process.TYPE_CHECKING:
            if self._has_all_jobs_passed(self._checking_jobs):
                logger.debug('checking jobs finished with success.')
                self.check_progress.setValue(100)
                self.btn_next.setEnabled(True)
            else:
                logger.debug('checking jobs finished with failure.')
            self.btn_check_start.setEnabled(True)
            self.btn_prev.setEnabled(True)
        elif Process.job_type == Process.TYPE_DEPLOYMENT:
            if self._has_all_jobs_passed(self._deployment_jobs):
                logger.debug('checking jobs finished with success.')
                self.deployment_progress.setValue(100)
                self.btn_next.setEnabled(True)
            else:
                logger.debug('checking jobs finished with failure.')
            self.btn_deployment_start.setEnabled(True)
            self.btn_prev.setEnabled(True)

    """Handlers for page 4: checking"""

    def _init_page4_checking(self):
        """Initialize Page 4, especially check items on the left."""
        Process.job_type = Process.TYPE_CHECKING
        if self._page4_inited:
            return

        Process.deploy_schema = self._deploy_schema

        for job in self._checking_jobs:
            job.setAutoDelete(False)
            job.status_widget = self._add_process_items(job.name, self.check_jobs)
            job.signals.summary_add.connect(self.slot_page4_page5_summary_add)
            job.signals.log_append.connect(self.slot_page4_page5_log_append)
            job.signals.log_overwrite_last_line.connect(self.slot_page4_page5_log_overwrite_last_line)
            job.signals.progress_value_change.connect(self.slot_page4_page5_progress_value_change)
            job.signals.finished.connect(self.slot_page4_page5_finished)

        self.check_jobs.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self._page4_inited = True

    @pyqtSlot()
    def slot_page4_check_start(self):
        self.btn_check_start.setEnabled(False)
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

        self.check_progress.setValue(0)
        self.checking_summary.clear()
        self.checking_log.clear()

        Process.progress_value = 0
        Process.all_stopped = False

        for i in range(self._checking_jobs.__len__()):
            self._thread_pool.start(self._checking_jobs[i])
            logger.debug("%d active threads in thread pool." % self._thread_pool.activeThreadCount())

    """Handlers for page 5: deployment"""

    def _init_page5_deployment(self):
        """Initialize Page 5, especially deployment items on the left."""
        Process.job_type = Process.TYPE_DEPLOYMENT
        if self._page5_inited:
            return

        Process.deploy_schema = self._deploy_schema

        for job in self._deployment_jobs:
            job.setAutoDelete(False)
            job.status_widget = self._add_process_items(job.name, self.deployment_jobs)
            job.signals.summary_add.connect(self.slot_page4_page5_summary_add)
            job.signals.log_append.connect(self.slot_page4_page5_log_append)
            job.signals.log_overwrite_last_line.connect(self.slot_page4_page5_log_overwrite_last_line)
            job.signals.progress_value_change.connect(self.slot_page4_page5_progress_value_change)
            job.signals.finished.connect(self.slot_page4_page5_finished)

        self.deployment_jobs.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self._page5_inited = True

    @pyqtSlot()
    def slot_page5_deployment_start(self):
        self.btn_deployment_start.setEnabled(False)
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

        self.deployment_progress.setValue(0)
        self.deployment_summary.clear()
        self.deployment_log.clear()

        Process.progress_value = 0
        Process.all_stopped = False

        for i in range(self._deployment_jobs.__len__()):
            self._thread_pool.start(self._deployment_jobs[i])
            logger.debug("%d active threads in thread pool." % self._thread_pool.activeThreadCount())
