from .constant import Constant
from .exceptions import RoleNotKnown
from .log import Log


class Node():
    _repo_lowest_prio = 94

    def __init__(self,
                 name,
                 fqdn,
                 roles,
                 networks,
                 public_address=None,
                 cluster_address=None,
                 storage_disks=None,
                 ram=None,
                 cpus=None,
                 repo_priority=None):
        self.name = name
        self.fqdn = fqdn
        self.roles = roles
        self.networks = networks
        self.public_address = public_address
        self.cluster_address = cluster_address
        if storage_disks is None:
            storage_disks = []
        self.storage_disks = storage_disks
        self.ram = ram
        self.cpus = cpus
        self.status = None
        self.repos = []
        self.repo_priority = repo_priority

    def has_role(self, role):
        if role not in Constant.KNOWN_ROLES:
            raise RoleNotKnown(role)
        return role in self.roles

    def has_roles(self):
        Log.debug("Node {}: has_roles: self.roles: {}".format(self.fqdn, self.roles))
        return bool(self.roles)

    def has_exclusive_role(self, role):
        Log.debug("Node {}: has_exclusive_role: self.roles: {}"
                  .format(self.fqdn, self.roles))
        if role not in Constant.KNOWN_ROLES:
            raise RoleNotKnown(role)
        return self.roles == [role]

    def add_repo(self, repo):
        if self.repo_priority:
            if repo.priority is None:
                repo.priority = self._repo_lowest_prio - len(self.repos)
        else:
            repo.priority = None
        self.repos.append(repo)


class NodeManager:
    def __init__(self, nodes):
        self.nodes = nodes

    def get_by_role(self, role):
        return [n for n in self.nodes if n.has_role(role)]

    def get_one_by_role(self, role):
        node_list = self.get_by_role(role)
        if node_list:
            return node_list[0]
        return None

    def get_by_name(self, name):
        for node in self.nodes:
            if node.name == name:
                return node
        return None

    def count_by_role(self, role):
        return len(self.get_by_role(role))
