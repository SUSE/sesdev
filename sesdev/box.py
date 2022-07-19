import click

from seslib.box import Box
from seslib.deployment import Deployment
from seslib.log import Log
from seslib.settings import Settings


def _pluralize_msg(an_iterable, singular, plural):
    if len(an_iterable) == 0:
        return "nothing"
    if len(an_iterable) == 1:
        return singular
    return plural


def box_list_handler(box_name, **kwargs):
    Log.debug("box_list_handler: called with box_name ->{}<-".format(box_name))
    settings_dict = _gen_box_settings_dict(**kwargs)
    settings = Settings(**settings_dict)
    box_obj = Box(settings)
    boxes_to_list = box_obj.maybe_glob_boxes(box_name)
    if len(boxes_to_list) == 0:
        click.echo("No Vagrant Boxes found")
    else:
        for box in boxes_to_list:
            click.echo(box)


def box_remove_handler(box_name, **kwargs):
    settings_dict = _gen_box_settings_dict(**kwargs)
    interactive = not settings_dict.get('non_interactive', False)
    settings = Settings(**settings_dict)
    box_obj = Box(settings)

    boxes_to_remove = box_obj.maybe_glob_boxes(box_name, simple=True)
    if not boxes_to_remove:
        return None

    box_word = _pluralize_msg(boxes_to_remove, "Vagrant Box", "Vagrant Boxes")

    if interactive:
        if boxes_to_remove:
            click.echo(f"You have asked to remove the following {box_word}")
            click.echo("---------------------------------------" + len(box_word) * '-')
            for box_to_remove in boxes_to_remove:
                click.echo(box_to_remove)
            click.echo()
    #
    # remove the boxes
    deps = Deployment.list(True)
    problems_encountered = False
    boxes_removed_count = 0
    for box_being_removed in boxes_to_remove:
        Log.info(f"Attempting to remove Vagrant Box >> {box_being_removed} << ...")
        #
        # existing deployments might be using this box
        existing_deployments = []
        for dep in deps:
            if box_being_removed == dep.settings.os:
                existing_deployments.append(dep.dep_id)

        if existing_deployments:
            dep_word = _pluralize_msg(existing_deployments, "deployment is", "deployments are")
            Log.warning(f"The following {dep_word} already using Vagrant Box "
                        f">> {box_being_removed} <<:")

            for dep_id in existing_deployments:
                Log.warning("        {}".format(dep_id))

            dep_word2 = _pluralize_msg(existing_deployments, "It", "These")
            Log.warning(f"{dep_word2} must be destroyed first!\n")
            problems_encountered = True
            continue

        really = True
        if interactive:
            really = click.confirm(f"Do you really want to remove box "
                                   f">> {box_being_removed} << ?", default=True)
        if not really:
            continue

        image_to_remove = box_obj.get_image_by_box(box_being_removed)
        if image_to_remove:
            Log.info("Found related image ->{}<- in libvirt storage pool"
                     .format(image_to_remove))
            box_obj.remove_image(image_to_remove)
            Log.info("Libvirt image removed.")
        box_obj.remove_box(box_being_removed)
        Log.info(f"Vagrant Box >> {box_being_removed} << removed.")
        boxes_removed_count += 1
    if boxes_removed_count != 1:
        click.echo(f"{boxes_removed_count} Vagrant Boxes were removed")
    if problems_encountered:
        Log.warning(f"sesdev tried to remove {boxes_to_remove} Vagrant Box(es), but "
                    "problems were encountered.")
        click.echo("Use \"sesdev box list\" to check current state")
    return None


def _gen_box_settings_dict(libvirt_host,
                           libvirt_user,
                           libvirt_private_key_file,
                           libvirt_storage_pool,
                           libvirt_networks,
                           all_boxes=None,
                           non_interactive=None,
                           force=None,
                           ):
    settings_dict = {}

    if all_boxes:
        pass

    if non_interactive or force:
        settings_dict['non_interactive'] = True

    if libvirt_host:
        settings_dict['libvirt_host'] = libvirt_host

    if libvirt_user:
        settings_dict['libvirt_user'] = libvirt_user

    if libvirt_private_key_file:
        settings_dict['libvirt_private_key_file'] = libvirt_private_key_file

    if libvirt_storage_pool:
        settings_dict['libvirt_storage_pool'] = libvirt_storage_pool

    if libvirt_networks:
        settings_dict['libvirt_networks'] = libvirt_networks

    return settings_dict
