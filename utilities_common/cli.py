import os
import sys
import netaddr
import subprocess

import click

from utilities_common.db import Db

from sonic_py_common import logger
from swsssdk import ConfigDBConnector

SYSLOG_IDENTIFIER_FOR_CONFIG = "config"
VLAN_SUB_INTERFACE_SEPARATOR = '.'

pass_db = click.make_pass_decorator(Db, ensure=True)

# Global logger instance
cfglog = logger.Logger(SYSLOG_IDENTIFIER_FOR_CONFIG)

class AbbreviationGroup(click.Group):
    """This subclass of click.Group supports abbreviated subgroup/subcommand names
    """

    def get_command(self, ctx, cmd_name):
        # Try to get builtin commands as normal
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # Allow automatic abbreviation of the command.  "status" for
        # instance will match "st".  We only allow that however if
        # there is only one command.
        # If there are multiple matches and the shortest one is the common prefix of all the matches, return
        # the shortest one
        matches = []
        shortest = None
        for x in self.list_commands(ctx):
            if x.lower().startswith(cmd_name.lower()):
                matches.append(x)
                if not shortest:
                    shortest = x
                elif len(shortest) > len(x):
                    shortest = x

        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        else:
            for x in matches:
                if not x.startswith(shortest):
                    break
            else:
                return click.Group.get_command(self, ctx, shortest)

            ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))

class AliasedGroup(click.Group):
    """This subclass of click.Group supports abbreviations and
       looking up aliases in a config file with a bit of magic.
    """

    def get_command(self, ctx, cmd_name):
        global _config

        # If we haven't instantiated our global config, do it now and load current config
        if _config is None:
            _config = Config()

            # Load our config file
            cfg_file = os.path.join(os.path.dirname(__file__), 'aliases.ini')
            _config.read_config(cfg_file)

        # Try to get builtin commands as normal
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # No builtin found. Look up an explicit command alias in the config
        if cmd_name in _config.aliases:
            actual_cmd = _config.aliases[cmd_name]
            return click.Group.get_command(self, ctx, actual_cmd)

        # Alternative option: if we did not find an explicit alias we
        # allow automatic abbreviation of the command.  "status" for
        # instance will match "st".  We only allow that however if
        # there is only one command.
        matches = [x for x in self.list_commands(ctx)
                   if x.lower().startswith(cmd_name.lower())]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))

class InterfaceAliasConverter(object):
    """Class which handles conversion between interface name and alias"""

    def __init__(self, db=None):

        if db is None:
            self.config_db = ConfigDBConnector()
            self.config_db.connect()
        else:
            self.config_db = db.cfgdb

        self.alias_max_length = 0
        self.port_dict = self.config_db.get_table('PORT')

        if not self.port_dict:
            click.echo(message="Warning: failed to retrieve PORT table from ConfigDB!", err=True)
            self.port_dict = {}

        for port_name in self.port_dict.keys():
            try:
                if self.alias_max_length < len(
                        self.port_dict[port_name]['alias']):
                   self.alias_max_length = len(
                        self.port_dict[port_name]['alias'])
            except KeyError:
                break

    def name_to_alias(self, interface_name):
        """Return vendor interface alias if SONiC
           interface name is given as argument
        """
        vlan_id = ''
        sub_intf_sep_idx = -1
        if interface_name is not None:
            sub_intf_sep_idx = interface_name.find(VLAN_SUB_INTERFACE_SEPARATOR)
            if sub_intf_sep_idx != -1:
                vlan_id = interface_name[sub_intf_sep_idx + 1:]
                # interface_name holds the parent port name
                interface_name = interface_name[:sub_intf_sep_idx]

            for port_name in self.port_dict.keys():
                if interface_name == port_name:
                    return self.port_dict[port_name]['alias'] if sub_intf_sep_idx == -1 \
                            else self.port_dict[port_name]['alias'] + VLAN_SUB_INTERFACE_SEPARATOR + vlan_id

        # interface_name not in port_dict. Just return interface_name
        return interface_name if sub_intf_sep_idx == -1 else interface_name + VLAN_SUB_INTERFACE_SEPARATOR + vlan_id

    def alias_to_name(self, interface_alias):
        """Return SONiC interface name if vendor
           port alias is given as argument
        """
        vlan_id = ''
        sub_intf_sep_idx = -1
        if interface_alias is not None:
            sub_intf_sep_idx = interface_alias.find(VLAN_SUB_INTERFACE_SEPARATOR)
            if sub_intf_sep_idx != -1:
                vlan_id = interface_alias[sub_intf_sep_idx + 1:]
                # interface_alias holds the parent port alias
                interface_alias = interface_alias[:sub_intf_sep_idx]

            for port_name in self.port_dict.keys():
                if interface_alias == self.port_dict[port_name]['alias']:
                    return port_name if sub_intf_sep_idx == -1 else port_name + VLAN_SUB_INTERFACE_SEPARATOR + vlan_id

        # interface_alias not in port_dict. Just return interface_alias
        return interface_alias if sub_intf_sep_idx == -1 else interface_alias + VLAN_SUB_INTERFACE_SEPARATOR + vlan_id

def get_interface_naming_mode():
    mode = os.getenv('SONIC_CLI_IFACE_MODE')
    if mode is None:
        mode = "default"
    return mode

def is_ipaddress(val):
    """ Validate if an entry is a valid IP """
    if not val:
        return False
    try:
        netaddr.IPAddress(str(val))
    except netaddr.core.AddrFormatError:
        return False
    return True


def is_ip_prefix_in_key(key):
    '''
    Function to check if IP address is present in the key. If it
    is present, then the key would be a tuple or else, it shall be
    be string
    '''
    return (isinstance(key, tuple))

def is_valid_port(config_db, port):
    """Check if port is in PORT table"""

    port_table = config_db.get_table('PORT')
    if port in port_table.keys():
        return True

    return False

def is_valid_portchannel(config_db, port):
    """Check if port is in PORT_CHANNEL table"""

    pc_table = config_db.get_table('PORTCHANNEL')
    if port in pc_table.keys():
        return True

    return False

def is_vlanid_in_range(vid):
    """Check if vlan id is valid or not"""

    if vid >= 1 and vid <= 4094:
        return True

    return False

def check_if_vlanid_exist(config_db, vlan):
    """Check if vlan id exits in the config db or ot"""

    if len(config_db.get_entry('VLAN', vlan)) != 0:
        return True

    return False

def is_port_vlan_member(config_db, port, vlan):
    """Check if port is a member of vlan"""

    vlan_ports_data = config_db.get_table('VLAN_MEMBER')
    for key in vlan_ports_data.keys():
        if key[0] == vlan and key[1] == port:

def interface_is_in_vlan(vlan_member_table, interface_name):
    """ Check if an interface  is in a vlan """
    for _,intf in vlan_member_table.keys():
        if intf == interface_name:
            return True

    return False

def interface_is_in_portchannel(portchannel_member_table, interface_name):
    """ Check if an interface is part of portchannel """
    for _,intf in portchannel_member_table.keys():
        if intf == interface_name:
            return True

    return False

def is_port_router_interface(config_db, port):
    """Check if port is a router interface"""

    interface_table = config_db.get_table('INTERFACE')
    for intf in interface_table.keys():
        if port == intf[0]:
            return True

	return False

def is_pc_router_interface(config_db, pc):
    """Check if portchannel is a router interface"""

    pc_interface_table = config_db.get_table('PORTCHANNEL_INTERFACE')
    for intf in pc_interface_table.keys():
        if pc == intf[0]:
            return True

    return False

def is_port_mirror_dst_port(config_db, port):
    """ Check if port is already configured as mirror destination port """
    mirror_table = config_db.get_table('MIRROR_SESSION')
    for _,v in mirror_table.items():
        if 'dst_port' in v and v['dst_port'] == port:
            return True

    return False

def interface_has_mirror_config(mirror_table, interface_name):
    """ Check if port is already configured with mirror config """
    for _,v in mirror_table.items():
        if 'src_port' in v and v['src_port'] == interface_name:
            return True
        if 'dst_port' in v and v['dst_port'] == interface_name:
            return True

    return False

def run_command(command, display_cmd=False, ignore_error=False):
    """Run bash command and print output to stdout
    """

    if display_cmd == True:
        click.echo(click.style("Running command: ", fg='cyan') + click.style(command, fg='green'))

    if os.environ["UTILITIES_UNIT_TESTING"] == "1":
        return

    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    (out, err) = proc.communicate()

    if len(out) > 0:
        click.echo(out)

    if proc.returncode != 0 and not ignore_error:
        sys.exit(proc.returncode)
