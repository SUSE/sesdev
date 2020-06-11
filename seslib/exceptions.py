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


class VersionNotKnown(SesDevException):
    def __init__(self, version):
        super(VersionNotKnown, self).__init__(
            "Unknown deployment version: '{}'".format(version))


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


class OptionValueError(SesDevException):
    def __init__(self, option, message, value):
        super(OptionValueError, self).__init__(
            "Wrong value for option '{}'. {}. Actual value: '{}'"
            .format(option, message, value))


class OptionFormatError(SesDevException):
    def __init__(self, option, expected_type, value):
        super(OptionFormatError, self).__init__(
            "Wrong format for option '{}': expected format: '{}', actual format: '{}'"
            .format(option, expected_type, value))


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


class RoleNotKnown(SesDevException):
    def __init__(self, role):
        super(RoleNotKnown, self).__init__(
            "Role '{}' is not supported by sesdev".format(role))


class RoleNotSupported(SesDevException):
    def __init__(self, role, version):
        super(RoleNotSupported, self).__init__(
            "Role '{}' is not supported in version '{}'".format(role, version))


class NoPrometheusGrafanaInSES5(SesDevException):
    def __init__(self):
        super(NoPrometheusGrafanaInSES5, self).__init__(
            "The DeepSea version used in SES5 does not recognize 'prometheus' "
            "or 'grafana' as roles in policy.cfg (instead, it _always_ deploys "
            "these two services on the Salt Master node. For this reason, sesdev "
            "does not permit these roles to be used with ses5."
            )


class UniqueRoleViolation(SesDevException):
    def __init__(self, role, number):
        super(UniqueRoleViolation, self).__init__(
            "There must be one, and only one, '{role}' role "
            "(you gave {number} '{role}' roles)".format(role=role, number=number)
            )


class VagrantSshConfigNoHostName(SesDevException):
    def __init__(self, name):
        super(VagrantSshConfigNoHostName, self).__init__(
            "Could not get HostName info from 'vagrant ssh-config {}' command"
            .format(name))


class ScpInvalidSourceOrDestination(SesDevException):
    def __init__(self):
        super(ScpInvalidSourceOrDestination, self).__init__(
            "Either source or destination must contain a ':' - not both or neither")


class SettingNotKnown(SesDevException):
    def __init__(self, setting):
        super(SettingNotKnown, self).__init__(
            "Setting '{}' is not known - please open a bug report!".format(setting))


class SupportconfigOnlyOnSLE(SesDevException):
    def __init__(self):
        super(SupportconfigOnlyOnSLE, self).__init__(
            "sesdev supportconfig depends on the 'supportconfig' RPM, which is "
            "available only on SUSE Linux Enterprise"
            )


class BadMakeCheckRolesNodes(SesDevException):
    def __init__(self):
        super(BadMakeCheckRolesNodes, self).__init__(
            "\"makecheck\" deployments only work with a single node with role "
            "\"makecheck\". Since this is the default, you can simply omit "
            "the --roles option when running \"sesdev create makecheck\"."
            )


class DuplicateRolesNotSupported(SesDevException):
    def __init__(self, role):
        super(DuplicateRolesNotSupported, self).__init__(
            "A node with more than one \"{r}\" role was detected. "
            "sesdev does not support more than one \"{r}\" role per node.".format(r=role)
            )


class NoSupportConfigTarballFound(SesDevException):
    def __init__(self, node):
        super(NoSupportConfigTarballFound, self).__init__(
            "No supportconfig tarball found on node {}".format(node))


class ExplicitAdminRoleNotAllowed(SesDevException):
    def __init__(self):
        super(ExplicitAdminRoleNotAllowed, self).__init__(
            "Though it is still recognized in existing deployments, the explicit "
            "\"admin\" role is deprecated and new deployments are not allowed to "
            "have it. When sesdev deploys Ceph/SES versions that use an \"admin\" "
            "role, all nodes in the deployment will get that role implicitly. "
            "(TL;DR remove the \"admin\" role and try again!)")


class SubcommandNotSupportedInVersion(SesDevException):
    def __init__(self, subcmd, version):
        super(SubcommandNotSupportedInVersion, self).__init__(
            "Subcommand {} not supported in '{}'".format(subcmd, version))


class DepIDWrongLength(SesDevException):
    def __init__(self, length):
        super(DepIDWrongLength, self).__init__(
            "Deployment ID must be from 1 to 63 characters in length "
            "(yours had {} characters)".format(length))


class DepIDIllegalChars(SesDevException):
    def __init__(self, dep_id):
        super(DepIDIllegalChars, self).__init__(
            "dep_id \"{}\" contains illegal characters. Valid characters for hostnames "
            "are ASCII(7) letters from a to z, the digits from 0 to 9, and the "
            "hyphen (-).".format(dep_id))
