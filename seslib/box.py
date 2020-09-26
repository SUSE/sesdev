import fnmatch
import os
from xml.dom import minidom
import libvirt

from . import tools
from .constant import Constant
from .log import Log
from .tools import is_a_glob


class Box():
    # pylint: disable=no-member
    def __init__(self, settings):
        self.libvirt_use_ssh = settings.libvirt_use_ssh
        self.libvirt_private_key_file = settings.libvirt_private_key_file
        self.libvirt_user = settings.libvirt_user
        self.libvirt_host = settings.libvirt_host
        self.libvirt_storage_pool = (
            settings.libvirt_storage_pool if settings.libvirt_storage_pool else 'default'
        )
        self.libvirt_conn = None
        self.libvirt_uri = None
        self.pool = None
        self.all_possible_boxes = list(Constant.OS_BOX_MAPPING.keys()) + \
            list(Constant.OS_ALIASED_BOXES.keys())
        self._populate_box_list()

    def _build_libvirt_uri(self):
        uri = None
        if self.libvirt_use_ssh:
            uri = 'qemu+ssh://'
            if self.libvirt_user:
                uri += "{}@".format(self.libvirt_user)
            assert self.libvirt_host, "Cannot use qemu+ssh without a host"
            uri += "{}/system".format(self.libvirt_host)
            if self.libvirt_private_key_file:
                if '/' not in self.libvirt_private_key_file:
                    self.libvirt_private_key_file = os.path.join(
                        os.path.expanduser('~'),
                        '.ssh',
                        self.libvirt_private_key_file
                    )
                uri += '?keyfile={}'.format(self.libvirt_private_key_file)
        else:
            uri = 'qemu:///system'
        self.libvirt_uri = uri

    def _populate_box_list(self):
        self.boxes = []
        cmd = ["vagrant", "box", "list"]
        output = tools.run_sync(cmd)
        lines = output.split('\n')
        for line in lines:
            if 'libvirt' in line:
                box_name = line.split()[0]
                if box_name in self.all_possible_boxes:
                    self.boxes.append(box_name)

    def exists(self, box_name):
        return box_name in self.boxes

    def get_image_by_box(self, box_name):
        #
        # open connection to libvirt server
        self.open_libvirt_connection()
        #
        # verify that the corresponding image exists in libvirt storage pool
        self.pool = self.libvirt_conn.storagePoolLookupByName(self.libvirt_storage_pool)
        removal_candidates = []
        for removal_candidate in self.pool.listVolumes():
            if str(removal_candidate).startswith('{}_vagrant_box_image'.format(box_name)):
                removal_candidates.append(removal_candidate)
        if len(removal_candidates) == 0:
            return None
        if len(removal_candidates) == 1:
            return removal_candidates[0]
        #
        # bad news - multiple images match the box name
        print("Images matching Vagrant Box ->{}<-".format(box_name))
        print("===================================================")
        for candidate in removal_candidates:
            print(candidate)
        print()
        assert False, \
            (
                "Too many matching images. Don't know which one to remove. "
                "This should not happen - please raise a bug!"
            )
        return None

    def get_images_by_deployment(self, dep_id):
        self.open_libvirt_connection()
        self.pool = self.libvirt_conn.storagePoolLookupByName(self.libvirt_storage_pool)
        matching_images = []
        for removal_candidate in self.pool.listVolumes():
            if str(matching_images).startswith(dep_id):
                matching_images.append(removal_candidate)
        return matching_images

    def get_networks_by_deployment(self, dep_id):
        self.open_libvirt_connection()
        domains = [x for x in self.libvirt_conn.listAllDomains() if
                   x.name().startswith(dep_id)]

        Log.debug("libvirt matching domains: {}".format(domains))

        networks = set()
        for domain in domains:
            xml = minidom.parseString(domain.XMLDesc())
            sources_lst = xml.getElementsByTagName("source")

            ifaces = [source for source in sources_lst if
                      source.parentNode.nodeName == "interface" and
                      source.parentNode.hasAttribute("type") and
                      source.parentNode.getAttribute("type") == "network"]

            Log.debug("libvirt domain's interfaces: {}".format(ifaces))

            for iface in ifaces:
                name = iface.getAttribute("network")
                if name == "vagrant-libvirt":
                    continue
                networks.add(name)
        return list(networks)

    @staticmethod
    def dehumanize_box_name(box_name):
        if box_name in Constant.OS_BOX_ALIASES:
            return Constant.OS_BOX_ALIASES[box_name]
        return box_name

    @staticmethod
    def humanize_box_name(box_name):
        if box_name in Constant.OS_ALIASED_BOXES:
            return Constant.OS_ALIASED_BOXES[box_name]
        return box_name

    def maybe_glob_boxes(self, box_spec, **kwargs):
        simple_list = kwargs.get('simple', False)
        all_boxes = self.printable_list(simple=True)
        all_boxes_with_aliases = self.printable_list(simple=False)
        matching_boxes = None
        if isinstance(box_spec, str):
            if is_a_glob(box_spec):
                matching_boxes = fnmatch.filter(all_boxes, box_spec)
            else:
                Log.info("{} is not a glob".format(box_spec))
                if box_spec == self.dehumanize_box_name(box_spec):
                    Log.info("{} is not an alias".format(box_spec))
                    matching_boxes = fnmatch.filter(all_boxes, box_spec)
                else:
                    matching_boxes = [self.dehumanize_box_name(box_spec)]
        else:
            matching_boxes = all_boxes
        assert isinstance(matching_boxes, list), \
            "maybe_glob_boxes: matching_boxes is not a list! Bailing out!"
        if matching_boxes:
            if not simple_list:
                for list_line in all_boxes_with_aliases:
                    literal_box_name = list_line.split()[0]
                    if literal_box_name in matching_boxes:
                        index = matching_boxes.index(literal_box_name)
                        matching_boxes[index] = list_line
        return matching_boxes

    def open_libvirt_connection(self):
        if self.libvirt_conn:
            return None
        self._build_libvirt_uri()
        # print("Opening libvirt connection to ->{}<-".format(self.libvirt_uri))
        self.libvirt_conn = libvirt.open(self.libvirt_uri)
        return None

    def printable_list(self, **kwargs):
        box_list = []
        simple_list = kwargs.get('simple', None)
        Log.info("printable_list: simple_list: {}".format(simple_list))
        for box in self.boxes:
            what_to_append = ''
            alias = ''
            if box in Constant.OS_ALIASED_BOXES:
                if simple_list:
                    what_to_append = box
                else:
                    alias = '(alias: {})'.format(self.humanize_box_name(box))
                    what_to_append = '{} {}'.format(box, alias)
            else:
                what_to_append = box
            box_list.append('{}'.format(what_to_append))
        return box_list

    def remove_image(self, image_name):
        image = self.pool.storageVolLookupByName(image_name)
        image.delete()

    @staticmethod
    def remove_box(box_name):
        tools.run_sync(["vagrant", "box", "remove", box_name])

    def destroy_network(self, name):
        self.open_libvirt_connection()

        try:
            network = self.libvirt_conn.networkLookupByName(name)
        except libvirt.libvirtError:
            Log.warning("Unable to find network '{}' for removal".format(name))
            return False

        try:
            network.destroy()
        except libvirt.libvirtError:
            Log.error("Something went wrong destroying network '{}'".format(name))
            return False

        return True
