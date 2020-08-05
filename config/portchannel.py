import click

from utilities_common.cli import AbbreviationGroup, pass_db

#
# 'portchannel' group ('config portchannel ...')
#
@click.group(cls=AbbreviationGroup)
def portchannel():
    """Configure port channel"""
    pass

@portchannel.command('add')
@click.argument('portchannel_name', metavar='<portchannel_name>', required=True)
@click.option('--min-links', default=0, type=int)
@click.option('--fallback', default='false')
@pass_db
def add_portchannel(db, portchannel_name, min_links, fallback):
    """Add port channel"""
    fvs = {'admin_status': 'up',
           'mtu': '9100'}
    if min_links != 0:
        fvs['min_links'] = str(min_links)
    if fallback != 'false':
        fvs['fallback'] = 'true'
    db.cdb.set_entry('PORTCHANNEL', portchannel_name, fvs)

@portchannel.command('del')
@click.argument('portchannel_name', metavar='<portchannel_name>', required=True)
@pass_db
def remove_portchannel(db, portchannel_name):
    """Remove port channel"""
    db.cdb.set_entry('PORTCHANNEL', portchannel_name, None)

@portchannel.group(cls=AbbreviationGroup, name='member')
def portchannel_member():
    """Configure port channel member"""
    pass

@portchannel_member.command('add')
@click.argument('portchannel_name', metavar='<portchannel_name>', required=True)
@click.argument('port_name', metavar='<port_name>', required=True)
@pass_db
def add_portchannel_member(db, portchannel_name, port_name):
    """Add member to port channel"""
    if interface_is_mirror_dst_port(db.cdb, port_name):
        ctx.fail("{} is configured as mirror destination port".format(port_name))
    db.cdb.set_entry('PORTCHANNEL_MEMBER', (portchannel_name, port_name),
            {'NULL': 'NULL'})

@portchannel_member.command('del')
@click.argument('portchannel_name', metavar='<portchannel_name>', required=True)
@click.argument('port_name', metavar='<port_name>', required=True)
@pass_db
def del_portchannel_member(db, portchannel_name, port_name):
    """Remove member from portchannel"""
    db.cdb.set_entry('PORTCHANNEL_MEMBER', (portchannel_name, port_name), None)
    db.cdb.set_entry('PORTCHANNEL_MEMBER', portchannel_name + '|' + port_name, None)
