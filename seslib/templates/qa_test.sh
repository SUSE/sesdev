
{% set qa_test_script = "/home/vagrant/qa-test.sh" %}
{%- set qa_test_cmd = "/home/vagrant/sesdev-qa/health-ok.sh"
    ~ " --total-nodes=" ~ nodes|length
    ~ " --nfs-ganesha-nodes=" ~ ganesha_nodes
    ~ " --igw-nodes=" ~ igw_nodes
    ~ " --mds-nodes=" ~ mds_nodes
    ~ " --mgr-nodes=" ~ mgr_nodes
    ~ " --mon-nodes=" ~ mon_nodes
    ~ " --osd-nodes=" ~ storage_nodes
    ~ " --osds=" ~ total_osds
    ~ " --rgw-nodes=" ~ rgw_nodes
-%}

cat > {{ qa_test_script }} << EOF
#!/bin/bash
set -x
if [[ $(hostname) == master* ]] ; then
    {{ qa_test_cmd }}
fi
EOF
chmod 755 {{ qa_test_script }}

{% if qa_test is sameas true %}
{{ qa_test_cmd }}
{% endif %}
