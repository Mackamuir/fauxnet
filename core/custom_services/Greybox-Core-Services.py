from core.config import ConfigString, ConfigBool, Configuration
from core.services.base import CoreService, ShadowDir, ServiceMode

class Greybox_Keepalived(CoreService):
    name: str = "Keepalived"
    group: str = "Greybox"
    files: list[str] = ["backbone_keepalived.sh"]
    startup: list[str] = [f"bash {files[0]}"]
    shutdown: list[str] = ["/usr/bin/killall keepalived"]

    def get_text_template(self, name: str) -> str:
        return """ #!/bin/sh
        keepalived --vrrp --use-file /opt/fauxnet/core/config/backbone_keepalived.conf
        """

class Topgen_Loopback(CoreService):
    name: str = "Topgen-Loopback"
    group: str = "Greybox"
    directories: list[str] = ['/var/named/data']
    files: list[str] = ["topgen_loopback.sh"]
    startup: list[str] = [f"bash {files[0]}"]
    shutdown: list[str] = ["/usr/sbin/ip addr flush scope global dev lo"]

    def get_text_template(self, name: str) -> str:
        return """ #!/bin/sh
        for i in $(cat /opt/fauxnet/vhosts/*/hosts | awk '{print $1}' | sort -u); do
	        /usr/sbin/ip addr add $i scope global dev lo
	    done
        """

class Topgen_Named(CoreService):
    name: str = "Topgen-Named"
    group: str = "Greybox"
    directories: list[str] = ['/var/named/data']
    dependencies: list[str] = ['Topgen-Loopback']
    startup: list[str] = ["/usr/sbin/named -u bind -c /opt/fauxnet/config/named.conf"]
    validate: list[str] = ["nslookup 8.8.8.8 8.8.8.8"]
    shutdown: list[str] = ["/usr/sbin/rndc stop"]


class Topgen_Nginx(CoreService):
    name: str = "Topgen-Nginx"
    group: str = "Greybox"
    directories: list[str] = ['/var/log/nginx']
    dependencies: list[str] = ['Topgen-Loopback']
    startup: list[str] = ["/usr/sbin/nginx"]
    validate: list[str] = ["pidof nginx"]
    shutdown: list[str] = ["/usr/bin/pkill nginx"]

class Topgen_Dovecot(CoreService):
    name: str = "Topgen-Dovecot"
    group: str = "Greybox"
    directories: list[str] = ['/var/lib/postfix', '/var/spool/postfix', '/var/spool/mail']
    dependencies: list[str] = ['Topgen-Loopback']
    startup: list[str] = ["/usr/sbin/dovecot -c /var/lib/topgen/etc/postfix/dovecot.conf"]
    validate: list[str] = ["pidof dovecot"]
    shutdown: list[str] = ["/usr/sbin/dovecot -c /var/lib/topgen/etc/postfix/dovecot.conf stop"]

class Topgen_Postfix(CoreService):
    name: str = "Topgen-Postfix"
    group: str = "Greybox"
    directories: list[str] = ['/var/lib/postfix', '/var/spool/postfix', '/var/spool/mail']
    dependencies: list[str] = ['Topgen-Loopback']
    startup: list[str] = ["/usr/sbin/postfix -c /var/lib/topgen/etc/postfix start"]
    validate: list[str] = ["/usr/sbin/postfix -c /var/lib/topgen/etc/postfix status"]
    shutdown: list[str] = ["/usr/sbin/postfix -c /var/lib/topgen/etc/postfix stop"]

class KeaDhcpService(CoreService):
    name: str = "Kea DHCPv4 Server"
    group: str = "FauxNet"
    directories: list[str] = ["/etc/kea/", "/var/lib/kea", "/run/kea"]
    files: list[str] = ["/etc/kea/kea-dhcp4.conf"]
    executables: list[str] = ["kea-dhcp4"]
    startup: list[str] = ["touch /var/lib/kea/dhcp4.leases", "kea-dhcp4 -c /etc/kea/kea-dhcp4.conf"]
    validate: list[str] = ["pidof kea-dhcp4"]
    shutdown: list[str] = ["pkill -f kea-dhcp4"]
    validation_mode: ServiceMode = ServiceMode.NON_BLOCKING

    def data(self) -> dict[str]:
        subnets = []
        for iface in self.node.get_ifaces(control=False):
            for ip4 in iface.ip4s:
                if ip4.size == 1:
                    continue
                # divide the address space in half
                index = (ip4.size - 2) / 2
                rangelow = ip4[index]
                rangehigh = ip4[-2]
                subnets.append((ip4, rangelow, rangehigh, ip4.ip, iface))
        return dict(subnets=subnets)

class Community(CoreService):
    name: str = "Community"
    group: str = "FauxNet"
    directories: list[str] = ["/var/run"]
    executables: list[str] = ["/usr/bin/python3"]
    startup: list[str] = ["PYTHONUNBUFFERED=1 /usr/bin/python3 /opt/fauxnet/core/community/community.py > community.log 2>&1 &"]
    validate: list[str] = ["pgrep -f \"/usr/bin/python3 /opt/fauxnet/core/community/community.py\""]
    shutdown: list[str] = ["pkill -f \"/usr/bin/python3 /opt/fauxnet/core/community/community.py\""]
    shadow_directories: list[ShadowDir] = [
        ShadowDir(path="/opt/fauxnet/core/community")
    ]
    validation_mode: ServiceMode = ServiceMode.NON_BLOCKING