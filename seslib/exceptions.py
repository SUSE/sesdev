class SesDevException(Exception):
    pass


class AddRepoNoUpdateWithExplicitRepo(SesDevException):
    def __init__(self):
        super().__init__(
            "The --update option does not work with an explicit custom repo."
        )


class BadMakeCheckRolesNodes(SesDevException):
    def __init__(self):
        super().__init__(
            "\"makecheck\" deployments only work with a single node with role "
            "\"makecheck\". Since this is the default, you can simply omit "
            "the --roles option when running \"sesdev create makecheck\"."
        )


class BoxDoesNotExist(SesDevException):
    def __init__(self, box_name):
        super().__init__(
            "There is no Vagrant Box called \"{}\"".format(box_name)
        )


class CmdException(SesDevException):
    def __init__(self, command, retcode, stderr):
        super().__init__(
            "Command '{}' failed: ret={} stderr:\n{}"
            .format(command, retcode, stderr)
        )
        self.command = command
        self.retcode = retcode
        self.stderr = stderr


class DebugWithoutLogFileDoesNothing(SesDevException):
    def __init__(self):
        super().__init__(
            "--debug without --log-file has no effect (maybe you want --verbose?)"
        )


class DepIDIllegalChars(SesDevException):
    def __init__(self, dep_id):
        super().__init__(
            "Deployment ID \"{}\" contains illegal characters. Valid characters for "
            "hostnames are ASCII(7) letters from a to z, the digits from 0 to 9, and "
            "the hyphen (-).".format(dep_id)
        )


class DepIDWrongLength(SesDevException):
    def __init__(self, length):
        super().__init__(
            "Deployment ID must be from 1 to 63 characters in length "
            "(yours had {} characters)".format(length)
        )


class DeploymentAlreadyExists(SesDevException):
    def __init__(self, dep_id):
        super().__init__(
            "A deployment with the same id '{}' already exists".format(dep_id)
        )


class DeploymentDoesNotExists(SesDevException):
    def __init__(self, dep_id):
        super().__init__(
            "Deployment '{}' does not exist".format(dep_id)
        )


class DuplicateRolesNotSupported(SesDevException):
    def __init__(self, role):
        super().__init__(
            "A node with more than one \"{r}\" role was detected. "
            "sesdev does not support more than one \"{r}\" role per node.".format(r=role)
        )


class ExclusiveRoles(SesDevException):
    def __init__(self, role_a, role_b):
        super().__init__(
            "Cannot have both roles '{}' and '{}' in the same deployment"
            .format(role_a, role_b)
        )


class ExplicitAdminRoleNotAllowed(SesDevException):
    def __init__(self):
        super().__init__(
            "Though it is still recognized in existing deployments, the explicit "
            "\"admin\" role is deprecated and new deployments are not allowed to "
            "have it. When sesdev deploys Ceph/SES versions that use an \"admin\" "
            "role, all nodes in the deployment will get that role implicitly. "
            "(TL;DR remove the \"admin\" role and try again!)"
        )


class MultipleRolesPerMachineNotAllowedInCaaSP(SesDevException):
    def __init__(self):
        super().__init__(
            "Multiple roles per machine detected. This is not allowed in CaaSP "
            "clusters. For a single-node cluster, use the --single-node option "
            "or --roles=\"[master]\" (in this special case, the master node "
            "will function also as a worker node)"
        )


class NodeDoesNotExist(SesDevException):
    def __init__(self, node, deployment_id):
        super().__init__(
            "No such node '{}' in deployment '{}'"
            .format(node, deployment_id)
        )


class NodeMustBeAdminAsWell(SesDevException):
    def __init__(self, role):
        super().__init__(
            "Detected node with \"{role}\" role but no \"admin\" role. "
            "The {role} node must have the \"admin\" role -- otherwise "
            "\"ceph-salt apply\" will fail. Please make sure the node with "
            "the \"{role}\" role has the \"admin\" role as well"
            .format(role=role)
            )


class NoGaneshaRolePostNautilus(SesDevException):
    def __init__(self):
        super().__init__(
            "You specified a \"ganesha\" role. In cephadm, NFS-Ganesha daemons "
            "are referred to as \"nfs\" daemons, so in sesdev the role has been "
            "renamed to \"nfs\". Please change all instances of \"ganesha\" to "
            "\"nfs\" in your roles string and try again"
        )


class NoExplicitRolesWithSingleNode(SesDevException):
    def __init__(self):
        super().__init__(
            "The --roles and --single-node options are mutually exclusive. "
            "One may be given, or the other, but not both at the same time."
        )


class NoNodeWithRole(SesDevException):
    def __init__(self, deployment_id, role):
        super().__init__(
            "Deployment '{}' has no node with role '{}'"
            .format(deployment_id, role)
        )


class NoPrometheusGrafanaInSES5(SesDevException):
    def __init__(self):
        super().__init__(
            "The DeepSea version used in SES5 does not recognize 'prometheus' "
            "or 'grafana' as roles in policy.cfg (instead, it _always_ deploys "
            "these two services on the Salt Master node. For this reason, sesdev "
            "does not permit these roles to be used with ses5."
        )


class NoStorageRolesCephadm(SesDevException):
    def __init__(self, offending_role):
        super().__init__(
            "No \"storage\" roles were given, but currently sesdev does not "
            "support this due to the presence of one or more {} roles in the "
            "cluster configuration.".format(offending_role)
        )


class NoStorageRolesDeepsea(SesDevException):
    def __init__(self, version):
        super().__init__(
            "No \"storage\" roles were given, but currently sesdev does not "
            "support this configuration when deploying a {} "
            "cluster.".format(version)
        )


class NoSourcePortForPortForwarding(SesDevException):
    def __init__(self):
        super().__init__(
            "No source port specified for port forwarding"
        )


class NoSupportConfigTarballFound(SesDevException):
    def __init__(self, node):
        super().__init__(
            "No supportconfig tarball found on node {}".format(node)
        )


class OptionFormatError(SesDevException):
    def __init__(self, option, expected_type, value):
        super().__init__(
            "Wrong format for option '{}': expected format: '{}', actual format: '{}'"
            .format(option, expected_type, value)
        )


class OptionNotSupportedInContext(SesDevException):
    def __init__(self, option):
        super().__init__(
            "Option '{}' not supported in this context. Open a bug report if "
            "you need this functionality."
            .format(option)
        )


class OptionNotSupportedInVersion(SesDevException):
    def __init__(self, option, version):
        super().__init__(
            "Option '{}' not supported with version '{}'".format(option, version)
        )


class OptionValueError(SesDevException):
    def __init__(self, option, message, value):
        super().__init__(
            "Wrong value for option '{}'. {}. Actual value: '{}'"
            .format(option, message, value)
        )


class ProductOptionOnlyOnSES(SesDevException):
    def __init__(self, version):
        super().__init__(
            "You asked to create a {} cluster with the --product option, "
            "but this option only works with versions starting with \"ses\""
            .format(version)
        )


class RebootDidNotSucceed(SesDevException):
    def __init__(self, node, deployment_id):
        super().__init__(
            "Attempted to reboot node '{}' of deployment '{}', but ran into problems"
            .format(node, deployment_id)
        )


class RoleNotKnown(SesDevException):
    def __init__(self, role):
        super().__init__(
            "Role '{}' is not supported by sesdev".format(role)
        )


class RoleNotSupported(SesDevException):
    def __init__(self, role, version):
        super().__init__(
            "Role '{}' is not supported in version '{}'".format(role, version)
        )


class ScpInvalidSourceOrDestination(SesDevException):
    def __init__(self):
        super().__init__(
            "Either source or destination must contain a ':' - not both or neither"
        )


class ServiceNotFound(SesDevException):
    def __init__(self, service):
        super().__init__(
            "Service '{}' was not found in this deployment".format(service)
        )


class ServicePortForwardingNotSupported(SesDevException):
    def __init__(self, service):
        super().__init__(
            "Service '{}' not supported for port forwarding. Specify manually the service source "
            "and destination ports".format(service)
        )


class SettingIncompatibleError(SesDevException):
    def __init__(self, setting1, value1, setting2, value2):
        super().__init__(
            "Setting {} = {} and {} = {} are incompatible"
            .format(setting1, value1, setting2, value2)
        )


class SettingNotKnown(SesDevException):
    def __init__(self, setting):
        super().__init__(
            "Setting '{}' is not known - please open a bug report!".format(setting)
        )


class SettingTypeError(SesDevException):
    def __init__(self, setting, expected_type, value):
        super().__init__(
            "Wrong value type for setting '{}': expected type: '{}', actual value='{}' ('{}')"
            .format(setting, expected_type, value, type(value))
        )


class SubcommandNotSupportedInVersion(SesDevException):
    def __init__(self, subcmd, version):
        super().__init__(
            "Subcommand {} not supported in '{}'".format(subcmd, version)
        )


class SupportconfigOnlyOnSLE(SesDevException):
    def __init__(self):
        super().__init__(
            "sesdev supportconfig depends on the 'supportconfig' RPM, which is "
            "available only on SUSE Linux Enterprise"
        )


class UniqueRoleViolation(SesDevException):
    def __init__(self, role, number):
        super().__init__(
            "There must be one, and only one, '{role}' role "
            "(you gave {number} '{role}' roles)".format(role=role, number=number)
        )


class VagrantSshConfigNoHostName(SesDevException):
    def __init__(self, name):
        super().__init__(
            "Could not get HostName info from 'vagrant ssh-config {}' command"
            .format(name)
        )


class VersionNotKnown(SesDevException):
    def __init__(self, version):
        super().__init__(
            "Unknown deployment version: '{}'".format(version)
        )


class VersionOSNotSupported(SesDevException):
    def __init__(self, version, operating_system):
        super().__init__(
            "sesdev does not know how to deploy \"{}\" on operating system \"{}\""
            .format(version, operating_system)
        )


class UnsupportedVMEngine(SesDevException):
    def __init__(self, engine):
        super().__init__(
            "Unsupported VM engine ->{}<- encountered. This is a bug: please "
            "report it to the maintainers".format(engine)
        )


class UpgradeNotSupported(SesDevException):
    def __init__(self, from_version, to_version):
        super().__init__(
            "You asked to upgrade a '{}' node to '{}', but this combination "
            "is not supported".format(from_version, to_version)
        )


class YouMustProvide(SesDevException):
    def __init__(self, what):
        super().__init__(
            "You must provide {}".format(what)
        )
