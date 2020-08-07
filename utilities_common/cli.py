import click

from utilities_common.db import Db

pass_db = click.make_pass_decorator(Db, ensure=True)

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

def interface_is_router_port(interface_table, interface_name):
    """ Check if an interface has router config """
    for intf in interface_table.keys():
        if (interface_name == intf[0]):
            return True

    return False

def is_interface_mirror_dst_port(config_db, interface_name):
    """ Check if port is already configured as mirror destination port """
    mirror_table = config_db.get_table('MIRROR_SESSION')
    for _,v in mirror_table.items():
        if 'dst_port' in v and v['dst_port'] == interface_name:
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
