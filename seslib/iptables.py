from .constant import Constant
from .exceptions import FeatureNotAvailable
from .log import Log
from ipaddress import IPv4Network

try:
    # pylint: disable=import-error
    import iptc
    Constant.FEATURE["iptables"] = True
except ModuleNotFoundError:
    Constant.FEATURE["iptables"] = False


CHAIN = "LIBVIRT_FWI"


class IPTables():

    def __init__(self):
        if not Constant.FEATURE["iptables"]:
            raise FeatureNotAvailable("iptables")
        Log.info("Instantiating iptables object")
        self.table = iptc.Table(iptc.Table.FILTER)
        self.chain = iptc.Chain(self.table, "LIBVIRT_FWI")
        self.all_green = False

    @staticmethod
    def cidr_to_netmask(new_style):
        Log.debug("cidr_to_netmask: got network segment {}".format(new_style))
        ip_addr, prefixlen = new_style.split("/")
        Log.debug("cidr_to_netmask: split into {} and {}".format(ip_addr, prefixlen))
        assert prefixlen == "24", \
            "Encountered network with prefixlen other than 24! Bailing out!"
        return "{}/255.255.255.0".format(ip_addr)

    def dump_chain(self):
        print("Chain {} with {} rules:".format(CHAIN, len(self.chain.rules)))
        for rule in self.chain.rules:
            print("{}".format(iptc.easy.decode_iptc_rule(rule)))

    def traverse_chain(self, network1, network2):
        Log.info("traverse_chain: Traversing {} rules in chain {}"
                 .format(len(self.chain.rules), CHAIN)
                )
        self.new_rules = {
           network1: {},
           network2: {},
        }
        position = 0
        networks_already_set = 0
        for rule in self.chain.rules:
            position += 1
            decoded_rule = iptc.easy.decode_iptc_rule(rule)
            dst_network = decoded_rule.get('dst')
            Log.debug("traverse_chain: Examining rule {}".format(decoded_rule))
            Log.debug("traverse_chain: Destination network is {}".format(dst_network))
            if dst_network == network1 or dst_network == network2:
                if decoded_rule['target'] != 'ACCEPT':
                    continue
                print('found a rule that looks like this: {}'.format(decoded_rule))
                # {'dst': '10.20.134.0/24', 'out-interface': 'virbr3',
                # 'conntrack': {'ctstate': 'RELATED,ESTABLISHED'}, 'target':
                # 'ACCEPT', 'counters': (0, 0)}
                assert rule.src == '0.0.0.0/0.0.0.0', \
                    'Found rule has unexpected src property! Bailing out!'
                assert decoded_rule['conntrack'], \
                    'Found rule has no conntrack property! Bailing out!'
                assert dst_network in [network1, network2], \
                    'Found rule not one of the networks we were asked to link!  Bailing out!'
            if dst_network == network1:
                self.new_rules[network1]['src'] = network1
                self.new_rules[network1]['dst'] = network2
                self.new_rules[network1]['out-interface'] = decoded_rule['out-interface']
                self.new_rules[network1]['position'] = position
                if networks_already_set:
                    position += 2
                networks_already_set += 1
            if dst_network == network2:
                self.new_rules[network2]['src'] = network2
                self.new_rules[network2]['dst'] = network1
                self.new_rules[network2]['out-interface'] = decoded_rule['out-interface']
                self.new_rules[network2]['position'] = position
                if networks_already_set:
                    position += 2
                networks_already_set += 1
        # number of matching rules should be 2, one for each network to be
        # linked
        if networks_already_set == 2:
            self.all_green = True
        else:
            assert False, \
                "Did not find matching rules for both deployments!  Bailing out!"
        Log.info("traverse_chain: new rules {}".format(self.new_rules))

    def insert_new_rules(self):
        if self.all_green:
            rules_already_inserted = 0
            for ( _, data_for_new_rule) in self.new_rules.items():
                rule = iptc.Rule()
                rule.src = self.cidr_to_netmask(data_for_new_rule['src'])
                rule.out_interface = data_for_new_rule['out-interface']
                rule.dst = self.cidr_to_netmask(data_for_new_rule['dst'])
                rule.target = iptc.Target(rule, "ACCEPT")
                self.chain.insert_rule(rule, position=data_for_new_rule['position'])
                rules_already_inserted += 1
                rule = iptc.Rule()
                rule.src = self.cidr_to_netmask(data_for_new_rule['dst'])
                rule.out_interface = data_for_new_rule['out-interface']
                rule.dst = self.cidr_to_netmask(data_for_new_rule['src'])
                rule.target = iptc.Target(rule, "ACCEPT")
                self.chain.insert_rule(rule, position=data_for_new_rule['position'])
                rules_already_inserted += 1
            print("Inserted {} new rules into chain {}"
                  .format(rules_already_inserted, CHAIN)
                 )
