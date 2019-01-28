from chainup.host import Host


class DeploySchema(object):
    PRESET_TEST_SINGLE = 'preset_test_single'
    PRESET_TEST_FOUR = 'preset_test_four'
    PRESET_PROD_FOUR = 'preset_prod_four'
    CUSTOM_SCHEMA = 'custom'
    PLAYBOOKS_DIR = '~/.playbooks'

    def __init__(self):
        self.res_type = None
        self.schema = None

        self.chain_peer_port = '26656'
        self.chain_rpc_port = '26657'
        self.chain_proxy_app = 'kvstore'
        self.chain_home = '~/.trustchain'
        self.chain_crypto_sm = True
        self.num_chain_validators = 0
        self.num_chain_non_validators = 0

        self.ops_es_port = '9200'
        self.ops_monitor_home = '~/.monitor'
        self.ops_kibana_port = '5601'
        self.num_ops = 0

        self.chain_explorer_port = '8080'
        self.chain_explorer_home = '~/.explorer'
        self.num_chain_explorer = 0

        self.num_caserver = 0

    def preset_test_single(self):
        self.num_chain_validators = 1
        self.num_chain_non_validators = 0
        self.num_ops = 1
        self.num_chain_explorer = 1
        self.num_caserver = 0

    def preset_test_four(self):
        self.num_chain_validators = 4
        self.num_chain_non_validators = 0
        self.num_ops = 1
        self.num_chain_explorer = 1
        self.num_caserver = 0

    def preset_prod_four(self):
        self.num_chain_validators = 4
        self.num_chain_non_validators = 0
        self.num_ops = 3
        self.num_chain_explorer = 1
        self.num_caserver = 0


class HostDeploySchema(DeploySchema):
    def __init__(self):
        super().__init__()
        self.chain_validators = {}
        self.chain_non_validators = {}
        self.chain_explorers = {}
        self.ops_master = {}
        self.ops_workers = {}
        self.ca_servers = {}
        self.all_hosts = {}

    def add_or_update_host(self, host):
        self.remove_host(host.address)
        if host.has_role(Host.CHAIN_VALIDATOR):
            self.chain_validators.update({host.address: host})
        if host.has_role(Host.CHAIN_NON_VALIDATOR):
            self.chain_non_validators.update({host.address: host})
        if host.has_role(Host.CHAIN_EXPLORER):
            self.chain_explorers.update({host.address: host})
        if host.has_role(Host.OPS_MASTER):
            self.ops_master.update({host.address: host})
        if host.has_role(Host.OPS_WORKER):
            self.ops_workers.update({host.address: host})
        if host.has_role(Host.CA_SERVER):
            self.ca_servers.update({host.address: host})
        self.all_hosts.update({host.address: host})

    def remove_host(self, host_addr):
        self.chain_validators.pop(host_addr, None)
        self.chain_non_validators.pop(host_addr, None)
        self.chain_explorers.pop(host_addr, None)
        self.ops_master.pop(host_addr, None)
        self.ops_workers.pop(host_addr, None)
        self.ca_servers.pop(host_addr, None)
        self.all_hosts.pop(host_addr, None)

    def has_enough_chain_validators(self):
        return self.chain_validators.__len__() == self.num_chain_validators

    def has_enough_chain_non_validators(self):
        return self.chain_non_validators.__len__() == self.num_chain_non_validators

    def has_enough_chain_explorer(self):
        return self.chain_explorers.__len__() == self.num_chain_explorer

    def has_enough_ops(self):
        return self.ops_master.__len__() + self.ops_workers.__len__() == self.num_ops

    def has_enough_ca_servers(self):
        return self.ca_servers.__len__() == self.num_caserver

    def has_meet_schema(self):
        return (self.chain_validators.__len__() == self.num_chain_validators) \
               and (self.chain_non_validators.__len__() == self.num_chain_non_validators) \
               and (self.chain_explorers.__len__() == self.num_chain_explorer) \
               and (self.ops_master.__len__() + self.ops_workers.__len__() == self.num_ops) \
               and (self.ca_servers.__len__() == self.num_caserver)
