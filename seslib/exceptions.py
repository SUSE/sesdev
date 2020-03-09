class SesDevException(Exception):
    pass


class CmdException(SesDevException):
    def __init__(self, command, retcode, stderr):
        super(CmdException, self).__init__(
            "Command '{}' failed: ret={} stderr:\n{}"
            .format(command, retcode, stderr)
            )
        self.command = command
        self.retcode = retcode
        self.stderr = stderr


class DeploymentAlreadyExists(SesDevException):
    def __init__(self, dep_id):
        super(DeploymentAlreadyExists, self).__init__(
            "A deployment with the same id '{}' already exists".format(dep_id))


class DeploymentDoesNotExists(SesDevException):
    def __init__(self, dep_id):
        super(DeploymentDoesNotExists, self).__init__(
            "Deployment '{}' does not exist".format(dep_id))


class VersionOSNotSupported(SesDevException):
    def __init__(self, version, os):
        super(VersionOSNotSupported, self).__init__(
            "Combination of version '{}' and OS '{}' not supported".format(version, os))


class SettingIncompatibleError(SesDevException):
    def __init__(self, setting1, value1, setting2, value2):
        super(SettingIncompatibleError, self).__init__(
            "Setting {} = {} and {} = {} are incompatible"
            .format(setting1, value1, setting2, value2))


class SettingTypeError(SesDevException):
    def __init__(self, setting, expected_type, value):
        super(SettingTypeError, self).__init__(
            "Wrong value type for setting '{}': expected type: '{}', actual value='{}' ('{}')"
            .format(setting, expected_type, value, type(value)))


class VagrantBoxDoesNotExist(SesDevException):
    def __init__(self, box):
        super(VagrantBoxDoesNotExist, self).__init__(
            "The vagrant box '{}' does not exist. Please add it with `vagrant box add ...` command"
            .format(box))


class NodeDoesNotExist(SesDevException):
    def __init__(self, node):
        super(NodeDoesNotExist, self).__init__(
            "Node '{}' does not exist in this deployment".format(node))


class ServicePortForwardingNotSupported(SesDevException):
    def __init__(self, service):
        super(ServicePortForwardingNotSupported, self).__init__(
            "Service '{}' not supported for port forwarding. Specify manually the service source "
            "and destination ports".format(service))


class NoSourcePortForPortForwarding(SesDevException):
    def __init__(self):
        super(NoSourcePortForPortForwarding, self).__init__(
            "No source port specified for port forwarding")


class ServiceNotFound(SesDevException):
    def __init__(self, service):
        super(ServiceNotFound, self).__init__(
            "Service '{}' was not found in this deployment".format(service))


class ExclusiveRoles(SesDevException):
    def __init__(self, role_a, role_b):
        super(ExclusiveRoles, self).__init__(
            "Cannot have both roles '{}' and '{}' in the same deployment"
            .format(role_a, role_b))


class RoleNotSupported(SesDevException):
    def __init__(self, role, version):
        super(RoleNotSupported, self).__init__(
            "Role '{}' is not supported in version '{}'".format(role, version))


class VagrantSshConfigNoHostName(SesDevException):
    def __init__(self, name):
        super(VagrantSshConfigNoHostName, self).__init__(
            "Could not get HostName info from 'vagrant ssh-config {}' command"
            .format(name))


class ScpInvalidSourceOrDestination(SesDevException):
    def __init__(self):
        super(ScpInvalidSourceOrDestination, self).__init__(
            "Either source or destination must contain a ':' - not both or neither")


class MaxDisksExceeded(SesDevException):
    def __init__(self, max_disks):
        super(MaxDisksExceeded, self).__init__(
            "More than {} added disks is not supported"
            .format(max_disks))
