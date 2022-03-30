from seslib.constant import Constant
from seslib.tools import image_manifest_exists


def test_opensuse_org_images():
    for deployment_name, images in Constant.IMAGE_PATHS_DEVEL.items():
        print(deployment_name)
        for image_name, image_url in images.items():
            # We do not have any tests for hard-coded container images yet. This
            # is due to not reading them out in sesdev but also due to the
            # inability to query registry.suse.com for the manifests of the
            # container images, which is possible for registry.opensuse.org and
            # registry.suse.de.
            if image_url in ["registry.opensuse.org", "registry.suse.de"]:
                exists, resp = image_manifest_exists(image_url)
                msg = (
                    f"Container image {image_name} of deployment {deployment_name} not available"
                    f"Status Code: {resp.status_code}\tURL: {image_url}"
                )
                assert exists, msg

                print(f'\tFound container image "{image_name}" in "{image_url}"')
