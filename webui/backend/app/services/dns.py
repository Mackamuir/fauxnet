"""
DNS configuration generation and management service

This service provides functionality to:
- Parse and validate hosts files
- Manage DNS delegations
- Generate bind9 DNS configuration natively in Python
- View and manage DNS zones
"""

import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Set
from datetime import datetime
from app.schemas import (
    DNSHostEntry,
    DNSHostsFile,
    DNSDelegationEntry,
    DNSNameserverEntry,
    DNSDelegationsConfig,
    DNSConfiguration,
    DNSGenerationOptions,
    DNSZoneInfo,
    DNSGenerationResult,
    DNSStatus
)


# Hardcoded DNS infrastructure (well-known servers)
# Format: hostname -> list of IP addresses (supports multiple IPs per hostname)
CACHING_NS = {
    # Cloudflare
    'one.one.one.one': ['1.1.1.1', '1.0.0.1'],
    # Google
    'dns.google': ['8.8.8.8', '8.8.4.4'],
    # Quad9
    'dns.quad9.net': ['9.9.9.9', '149.112.112.112'],
    # Level 3
    'a.resolvers.level3.net': ['4.2.2.1'],
    'b.resolvers.level3.net': ['4.2.2.2'],
    'c.resolvers.level3.net': ['4.2.2.3'],
    'd.resolvers.level3.net': ['4.2.2.4'],
    'e.resolvers.level3.net': ['4.2.2.5'],
    'f.resolvers.level3.net': ['4.2.2.6'],
    # OpenDNS
    'resolver1.opendns.com': ['208.67.222.222'],
    'resolver2.opendns.com': ['208.67.220.220'],
}

TOPLEVEL_NS = {
    'ns.level3.net': ['4.4.4.8'],
    'ns.att.net': ['12.12.12.24'],
    'ns.verisign.com': ['69.58.181.181'],
}

ROOT_NS = {
    'a.root-servers.net': ['198.41.0.4'],
    'b.root-servers.net': ['192.228.79.201'],
    'c.root-servers.net': ['192.33.4.12'],
    'd.root-servers.net': ['199.7.91.13'],
    'e.root-servers.net': ['192.203.230.10'],
    'f.root-servers.net': ['192.5.5.241'],
    'g.root-servers.net': ['192.112.36.4'],
    'h.root-servers.net': ['128.63.2.53'],
    'i.root-servers.net': ['192.36.148.17'],
    'j.root-servers.net': ['192.58.128.30'],
    'k.root-servers.net': ['193.0.14.129'],
    'l.root-servers.net': ['199.7.83.42'],
    'm.root-servers.net': ['202.12.27.33'],
}



class DNSService:
    """Service for managing DNS configuration generation"""

    def __init__(self):
        self.default_config = DNSConfiguration()

    def get_status(self, config: Optional[DNSConfiguration] = None) -> DNSStatus:
        """Get current DNS configuration status"""
        if config is None:
            config = self.default_config

        # Check if vhosts config directory exists
        vhosts_exists = os.path.exists(config.vhosts_config_dir)
        mail_hosts_exists = os.path.exists(config.mail_hosts_path) if config.mail_hosts_path else False
        backbone_hosts_exists = os.path.exists(config.backbone_hosts_path) if config.backbone_hosts_path else False
        delegations_exists = os.path.exists(config.delegations_path)
        named_conf_exists = os.path.exists(config.output_named_conf_path)

        # Count zones
        zone_count = 0
        if os.path.exists(config.output_zone_folder):
            for subdir in ["rootsrv", "tldsrv"]:
                zone_dir = os.path.join(config.output_zone_folder, subdir)
                if os.path.exists(zone_dir):
                    zone_count += len([f for f in os.listdir(zone_dir) if f.endswith(".zone")])

        # Count web hosts from vhosts config directories
        web_hosts_count = 0
        vhost_hosts = self.get_vhost_hosts_files(config.vhosts_config_dir)
        web_hosts_count = sum(hf.line_count for hf in vhost_hosts)

        # Count mail hosts
        mail_hosts_count = 0
        if mail_hosts_exists:
            try:
                with open(config.mail_hosts_path, 'r') as f:
                    mail_hosts_count = sum(1 for line in f if line.strip() and not line.strip().startswith('#'))
            except Exception:
                pass

        # Count backbone hosts
        backbone_hosts_count = 0
        if backbone_hosts_exists:
            try:
                with open(config.backbone_hosts_path, 'r') as f:
                    backbone_hosts_count = sum(1 for line in f if line.strip() and not line.strip().startswith('#'))
            except Exception:
                pass

        # Check if regeneration is needed by comparing modification times
        needs_regeneration = self._check_needs_regeneration(config, vhost_hosts)

        return DNSStatus(
            configured=named_conf_exists,
            web_hosts_exists=vhosts_exists,
            mail_hosts_exists=mail_hosts_exists,
            backbone_hosts_exists=backbone_hosts_exists,
            delegations_exists=delegations_exists,
            named_conf_exists=named_conf_exists,
            zone_count=zone_count,
            web_hosts_count=web_hosts_count,
            mail_hosts_count=mail_hosts_count,
            backbone_hosts_count=backbone_hosts_count,
            needs_regeneration=needs_regeneration
        )

    def parse_hosts_file(self, file_path: str) -> List[DNSHostEntry]:
        """Parse a hosts file and return list of host entries"""
        entries = []

        if not os.path.exists(file_path):
            return entries

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Parse IP and FQDN
                    parts = line.split()
                    if len(parts) >= 2:
                        ip_address = parts[0]
                        fqdn = parts[1]

                        # Basic validation
                        if self._validate_ip(ip_address) and self._validate_fqdn(fqdn):
                            entries.append(DNSHostEntry(ip_address=ip_address, fqdn=fqdn))

        except Exception as e:
            raise Exception(f"Error parsing hosts file {file_path}: {str(e)}")

        return entries

    def get_vhost_hosts_files(self, vhosts_config_dir: str = "/opt/fauxnet/vhosts_config") -> List[DNSHostsFile]:
        """Get all vhost hosts files from /opt/fauxnet/vhosts_config/*/hosts"""
        hosts_files = []

        if not os.path.exists(vhosts_config_dir):
            return hosts_files

        try:
            # Find all vhost config directories
            for vhost_name in os.listdir(vhosts_config_dir):
                vhost_config_path = os.path.join(vhosts_config_dir, vhost_name)
                if not os.path.isdir(vhost_config_path):
                    continue

                hosts_file_path = os.path.join(vhost_config_path, "hosts")
                if os.path.exists(hosts_file_path):
                    entries = self.parse_hosts_file(hosts_file_path)
                    if entries:  # Only add if there are valid entries
                        hosts_files.append(DNSHostsFile(
                            name=vhost_name,
                            path=hosts_file_path,
                            entries=entries,
                            line_count=len(entries)
                        ))
        except Exception as e:
            # Log error but don't fail
            pass

        return hosts_files

    def get_hosts_files(self, config: Optional[DNSConfiguration] = None) -> List[DNSHostsFile]:
        """Get all configured hosts files with their contents"""
        if config is None:
            config = self.default_config

        hosts_files = []

        # Get vhost hosts files from vhosts_config_dir/*/hosts
        vhost_hosts = self.get_vhost_hosts_files(config.vhosts_config_dir)
        hosts_files.extend(vhost_hosts)

        # Backbone hosts (network infrastructure)
        if config.backbone_hosts_path and os.path.exists(config.backbone_hosts_path):
            entries = self.parse_hosts_file(config.backbone_hosts_path)
            hosts_files.append(DNSHostsFile(
                name="backbone",
                path=config.backbone_hosts_path,
                entries=entries,
                line_count=len(entries)
            ))

        # Custom hosts (manually added entries)
        if os.path.exists(config.custom_hosts_path):
            entries = self.parse_hosts_file(config.custom_hosts_path)
            hosts_files.append(DNSHostsFile(
                name="custom",
                path=config.custom_hosts_path,
                entries=entries,
                line_count=len(entries)
            ))

        # Mail hosts (still use centralized file)
        if config.mail_hosts_path and os.path.exists(config.mail_hosts_path):
            entries = self.parse_hosts_file(config.mail_hosts_path)
            hosts_files.append(DNSHostsFile(
                name="mail",
                path=config.mail_hosts_path,
                entries=entries,
                line_count=len(entries)
            ))

        # Extra hosts (for backward compatibility)
        for idx, extra_path in enumerate(config.extra_hosts_paths):
            if os.path.exists(extra_path):
                entries = self.parse_hosts_file(extra_path)
                hosts_files.append(DNSHostsFile(
                    name=f"extra{idx+1}",
                    path=extra_path,
                    entries=entries,
                    line_count=len(entries)
                ))

        return hosts_files

    def update_hosts_file(self, file_path: str, content: str) -> bool:
        """Update a hosts file with new content"""
        try:
            # Validate content first
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    raise ValueError(f"Invalid line format: {line}")

                if not self._validate_ip(parts[0]):
                    raise ValueError(f"Invalid IP address: {parts[0]}")

                if not self._validate_fqdn(parts[1]):
                    raise ValueError(f"Invalid FQDN: {parts[1]}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write content
            with open(file_path, 'w') as f:
                f.write(content)

            return True

        except Exception as e:
            raise Exception(f"Error updating hosts file: {str(e)}")

    def add_custom_dns_entry(self, ip_address: str, fqdn: str, config: Optional[DNSConfiguration] = None) -> bool:
        """Add a custom DNS entry to the custom hosts file"""
        if config is None:
            config = self.default_config

        try:
            # Validate input
            if not self._validate_ip(ip_address):
                raise ValueError(f"Invalid IP address: {ip_address}")
            if not self._validate_fqdn(fqdn):
                raise ValueError(f"Invalid FQDN: {fqdn}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(config.custom_hosts_path), exist_ok=True)

            # Read existing entries
            existing_entries = []
            if os.path.exists(config.custom_hosts_path):
                with open(config.custom_hosts_path, 'r') as f:
                    existing_entries = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

            # Check if FQDN already exists and update it, or add new entry
            updated = False
            for i, line in enumerate(existing_entries):
                parts = line.split()
                if len(parts) >= 2 and parts[1] == fqdn:
                    existing_entries[i] = f"{ip_address} {fqdn}"
                    updated = True
                    break

            if not updated:
                existing_entries.append(f"{ip_address} {fqdn}")

            # Write back
            with open(config.custom_hosts_path, 'w') as f:
                f.write('\n'.join(existing_entries) + '\n')

            return True

        except Exception as e:
            raise Exception(f"Error adding custom DNS entry: {str(e)}")

    def remove_custom_dns_entry(self, fqdn: str, config: Optional[DNSConfiguration] = None) -> bool:
        """Remove a custom DNS entry from the custom hosts file"""
        if config is None:
            config = self.default_config

        try:
            if not os.path.exists(config.custom_hosts_path):
                return False

            # Read existing entries
            existing_entries = []
            with open(config.custom_hosts_path, 'r') as f:
                existing_entries = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

            # Filter out the entry with matching FQDN
            filtered_entries = []
            found = False
            for line in existing_entries:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == fqdn:
                    found = True
                    continue
                filtered_entries.append(line)

            if not found:
                return False

            # Write back
            with open(config.custom_hosts_path, 'w') as f:
                if filtered_entries:
                    f.write('\n'.join(filtered_entries) + '\n')
                else:
                    f.write('')

            return True

        except Exception as e:
            raise Exception(f"Error removing custom DNS entry: {str(e)}")

    def add_mail_host_entry(self, ip_address: str, fqdn: str, config: Optional[DNSConfiguration] = None) -> bool:
        """Add a mail host entry to the mail hosts file"""
        if config is None:
            config = self.default_config

        try:
            # Validate input
            if not self._validate_ip(ip_address):
                raise ValueError(f"Invalid IP address: {ip_address}")
            if not self._validate_fqdn(fqdn):
                raise ValueError(f"Invalid FQDN: {fqdn}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(config.mail_hosts_path), exist_ok=True)

            # Read existing entries
            existing_entries = []
            if os.path.exists(config.mail_hosts_path):
                with open(config.mail_hosts_path, 'r') as f:
                    existing_entries = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

            # Check if FQDN already exists and update it, or add new entry
            updated = False
            for i, line in enumerate(existing_entries):
                parts = line.split()
                if len(parts) >= 2 and parts[1] == fqdn:
                    existing_entries[i] = f"{ip_address} {fqdn}"
                    updated = True
                    break

            if not updated:
                existing_entries.append(f"{ip_address} {fqdn}")

            # Write back
            with open(config.mail_hosts_path, 'w') as f:
                f.write('\n'.join(existing_entries) + '\n')

            return True

        except Exception as e:
            raise Exception(f"Error adding mail host entry: {str(e)}")

    def remove_mail_host_entry(self, fqdn: str, config: Optional[DNSConfiguration] = None) -> bool:
        """Remove a mail host entry from the mail hosts file"""
        if config is None:
            config = self.default_config

        try:
            if not os.path.exists(config.mail_hosts_path):
                return False

            # Read existing entries
            existing_entries = []
            with open(config.mail_hosts_path, 'r') as f:
                existing_entries = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

            # Filter out the entry with matching FQDN
            filtered_entries = []
            found = False
            for line in existing_entries:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == fqdn:
                    found = True
                    continue
                filtered_entries.append(line)

            if not found:
                return False

            # Write back
            with open(config.mail_hosts_path, 'w') as f:
                if filtered_entries:
                    f.write('\n'.join(filtered_entries) + '\n')
                else:
                    f.write('')

            return True

        except Exception as e:
            raise Exception(f"Error removing mail host entry: {str(e)}")

    def parse_delegations_file(self, file_path: str) -> DNSDelegationsConfig:
        """Parse the delegations file and return structured config"""
        forward = []
        reverse = []
        nameservers = []

        if not os.path.exists(file_path):
            return DNSDelegationsConfig(forward=forward, reverse=reverse, nameservers=nameservers)

        try:
            # Source the bash file and extract associative arrays
            with open(file_path, 'r') as f:
                content = f.read()

            # Parse DELEGATIONS_FWD
            fwd_match = re.search(r'declare -A DELEGATIONS_FWD=\((.*?)\)', content, re.DOTALL)
            if fwd_match:
                entries_text = fwd_match.group(1)
                for match in re.finditer(r"\['([^']+)'\]='([^']+)'", entries_text):
                    domain = match.group(1)
                    ns_list = match.group(2).split()
                    forward.append(DNSDelegationEntry(domain_or_network=domain, nameservers=ns_list))

            # Parse DELEGATIONS_REV
            rev_match = re.search(r'declare -A DELEGATIONS_REV=\((.*?)\)', content, re.DOTALL)
            if rev_match:
                entries_text = rev_match.group(1)
                for match in re.finditer(r"\['([^']+)'\]='([^']+)'", entries_text):
                    network = match.group(1)
                    ns_list = match.group(2).split()
                    reverse.append(DNSDelegationEntry(domain_or_network=network, nameservers=ns_list))

            # Parse DELEGATIONS_NS
            ns_match = re.search(r'declare -A DELEGATIONS_NS=\((.*?)\)', content, re.DOTALL)
            if ns_match:
                entries_text = ns_match.group(1)
                for match in re.finditer(r"\['([^']+)'\]='([^']+)'", entries_text):
                    hostname = match.group(1)
                    ip_address = match.group(2)
                    nameservers.append(DNSNameserverEntry(hostname=hostname, ip_address=ip_address))

        except Exception as e:
            raise Exception(f"Error parsing delegations file: {str(e)}")

        return DNSDelegationsConfig(forward=forward, reverse=reverse, nameservers=nameservers)

    def update_delegations_file(self, file_path: str, delegations: DNSDelegationsConfig) -> bool:
        """Update delegations file with new configuration"""
        try:
            # Generate bash associative arrays
            content = "#!/bin/bash\n\n"
            content += "# DNS Delegations Configuration\n"
            content += "# Generated by Fauxnet WebUI\n\n"

            # Forward delegations
            content += "declare -A DELEGATIONS_FWD=(\n"
            for entry in delegations.forward:
                ns_str = ' '.join(entry.nameservers)
                content += f"  ['{entry.domain_or_network}']='{ns_str}'\n"
            content += ")\n\n"

            # Reverse delegations
            content += "declare -A DELEGATIONS_REV=(\n"
            for entry in delegations.reverse:
                ns_str = ' '.join(entry.nameservers)
                content += f"  ['{entry.domain_or_network}']='{ns_str}'\n"
            content += ")\n\n"

            # Nameserver IPs
            content += "declare -A DELEGATIONS_NS=(\n"
            for entry in delegations.nameservers:
                content += f"  ['{entry.hostname}']='{entry.ip_address}'\n"
            content += ")\n"

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write content
            with open(file_path, 'w') as f:
                f.write(content)

            return True

        except Exception as e:
            raise Exception(f"Error updating delegations file: {str(e)}")

    def get_zone_files(self, config: Optional[DNSConfiguration] = None) -> List[DNSZoneInfo]:
        """Get list of generated zone files"""
        if config is None:
            config = self.default_config

        zones = []

        if not os.path.exists(config.output_zone_folder):
            return zones

        # Root server zones
        rootsrv_dir = os.path.join(config.output_zone_folder, "rootsrv")
        if os.path.exists(rootsrv_dir):
            for filename in os.listdir(rootsrv_dir):
                if filename.endswith(".zone"):
                    filepath = os.path.join(rootsrv_dir, filename)
                    zones.append(self._get_zone_info(filename, filepath, "root"))

        # TLD server zones
        tldsrv_dir = os.path.join(config.output_zone_folder, "tldsrv")
        if os.path.exists(tldsrv_dir):
            for filename in os.listdir(tldsrv_dir):
                if filename.endswith(".zone"):
                    filepath = os.path.join(tldsrv_dir, filename)

                    # Determine if forward or reverse
                    zone_type = "reverse" if filename[0].isdigit() else "forward"
                    zones.append(self._get_zone_info(filename, filepath, zone_type))

        return zones

    def get_zone_content(self, zone_path: str) -> str:
        """Get content of a zone file"""
        if not os.path.exists(zone_path):
            raise FileNotFoundError(f"Zone file not found: {zone_path}")

        with open(zone_path, 'r') as f:
            return f.read()

    def generate_dns_config(self, config: Optional[DNSConfiguration] = None,
                           options: Optional[DNSGenerationOptions] = None) -> DNSGenerationResult:
        """
        Generate DNS configuration natively in Python
        """
        if config is None:
            config = self.default_config

        if options is None:
            options = DNSGenerationOptions()

        warnings = []
        errors = []
        hosts_processed = 0
        hosts_skipped = 0

        try:
            # Setup paths
            root_zd = os.path.join(config.output_zone_folder, "rootsrv")
            tld_zd = os.path.join(config.output_zone_folder, "tldsrv")

            # Check for existing configuration
            if not options.force_overwrite:
                if os.path.exists(config.output_named_conf_path):
                    return DNSGenerationResult(
                        success=False,
                        zones_created=0,
                        hosts_processed=0,
                        hosts_skipped=0,
                        errors=[f"Configuration already exists at {config.output_named_conf_path}. Use force_overwrite=True to replace."]
                    )

            # Force overwrite if requested
            if options.force_overwrite:
                if os.path.exists(config.output_dns_hosts_path):
                    os.remove(config.output_dns_hosts_path)
                if os.path.exists(config.output_named_conf_path):
                    os.remove(config.output_named_conf_path)
                if os.path.exists(root_zd):
                    import shutil
                    shutil.rmtree(root_zd)
                if os.path.exists(tld_zd):
                    import shutil
                    shutil.rmtree(tld_zd)

            # Create output directories
            os.makedirs(os.path.dirname(config.output_dns_hosts_path), exist_ok=True)
            os.makedirs(os.path.dirname(config.output_named_conf_path), exist_ok=True)
            os.makedirs(root_zd, exist_ok=True)
            os.makedirs(tld_zd, exist_ok=True)

            # Load delegations
            delegations = self.parse_delegations_file(config.delegations_path)
            delegations_fwd_dict = {d.domain_or_network: d.nameservers for d in delegations.forward}
            delegations_rev_dict = {d.domain_or_network: d.nameservers for d in delegations.reverse}
            delegations_ns_dict = {d.hostname: d.ip_address for d in delegations.nameservers}

            # Build hosts list
            hosts_list = {}  # fqdn -> ip_addr
            domain_mx = {}   # domain -> list of mx servers

            # Process vhost hosts files from vhosts_config_dir/*/hosts
            vhost_hosts = self.get_vhost_hosts_files(config.vhosts_config_dir)
            for vhost_host_file in vhost_hosts:
                # Create a temp file path or use the actual path
                skip_count = self._add_hosts_to_list(
                    vhost_host_file.path, hosts_list, domain_mx,
                    delegations_fwd_dict, delegations_rev_dict,
                    is_mx=False, warnings=warnings, quiet=options.quiet_mode
                )
                hosts_skipped += skip_count

            # Process backbone hosts (network infrastructure)
            if config.backbone_hosts_path and os.path.exists(config.backbone_hosts_path):
                skip_count = self._add_hosts_to_list(
                    config.backbone_hosts_path, hosts_list, domain_mx,
                    delegations_fwd_dict, delegations_rev_dict,
                    is_mx=False, warnings=warnings, quiet=options.quiet_mode
                )
                hosts_skipped += skip_count

            # Process custom hosts (manually added entries)
            if os.path.exists(config.custom_hosts_path):
                skip_count = self._add_hosts_to_list(
                    config.custom_hosts_path, hosts_list, domain_mx,
                    delegations_fwd_dict, delegations_rev_dict,
                    is_mx=False, warnings=warnings, quiet=options.quiet_mode
                )
                hosts_skipped += skip_count

            # Process extra hosts (for backward compatibility)
            for extra_path in config.extra_hosts_paths:
                if os.path.exists(extra_path):
                    skip_count = self._add_hosts_to_list(
                        extra_path, hosts_list, domain_mx,
                        delegations_fwd_dict, delegations_rev_dict,
                        is_mx=False, warnings=warnings, quiet=options.quiet_mode
                    )
                    hosts_skipped += skip_count

            # Process mail hosts
            if config.mail_hosts_path and os.path.exists(config.mail_hosts_path):
                skip_count = self._add_hosts_to_list(
                    config.mail_hosts_path, hosts_list, domain_mx,
                    delegations_fwd_dict, delegations_rev_dict,
                    is_mx=True, warnings=warnings, quiet=options.quiet_mode
                )
                hosts_skipped += skip_count

            # Add delegation nameservers
            for ns, ip in delegations_ns_dict.items():
                if ns in hosts_list and hosts_list[ns] != ip:
                    if not options.quiet_mode:
                        warnings.append(f"Delegation nameserver {ns} already in hosts (old: {hosts_list[ns]}, new: {ip})")
                hosts_list[ns] = ip

            # Note: DNS infrastructure (CACHING_NS, TOPLEVEL_NS, ROOT_NS) is NOT added to hosts_list
            # because they can have multiple IPs per hostname. They are handled separately
            # in the zone generation loop.

            # Count total hosts (including DNS infrastructure)
            dns_infra_count = len(CACHING_NS) + len(TOPLEVEL_NS) + len(ROOT_NS)
            hosts_processed = len(hosts_list) + dns_infra_count

            # Generate DNS hosts file
            self._generate_dns_hosts_file(config.output_dns_hosts_path)

            # Generate named.conf
            self._generate_named_conf(config.output_named_conf_path, root_zd, tld_zd)

            # Generate root zone
            root_zone_path = os.path.join(root_zd, "root.zone")
            self._generate_root_zone(root_zone_path)

            # Track created zones
            created_zones = set()

            # Helper function to add A and PTR records for a hostname/IP pair
            def add_dns_records(fqdn, ipaddr):
                # Parse domain components
                tld = self._get_tld(fqdn)
                if not tld:
                    return

                # Create forward zone if needed
                if tld not in created_zones:
                    self._create_forward_zone(tld, tld_zd, config.output_named_conf_path, root_zone_path)
                    created_zones.add(tld)

                # Add A record
                zone_file = os.path.join(tld_zd, f"{tld}.zone")
                fqdn_without_tld = fqdn[:-len(tld)-1]  # Remove .tld
                with open(zone_file, 'a') as f:
                    f.write(f"{fqdn_without_tld}\tA\t{ipaddr}\n")

                # Add PTR record
                ip_parts = ipaddr.split('.')
                if len(ip_parts) == 4:
                    ip1 = ip_parts[0]
                    if ip1 not in created_zones:
                        self._create_reverse_zone(ip1, tld_zd, config.output_named_conf_path)
                        created_zones.add(ip1)

                    rev_zone_file = os.path.join(tld_zd, f"{ip1}.zone")
                    with open(rev_zone_file, 'a') as f:
                        f.write(f"{ip_parts[3]}.{ip_parts[2]}.{ip_parts[1]}\tPTR\t{fqdn}.\n")

            # Generate TLD zones and add records for regular hosts
            for fqdn, ipaddr in hosts_list.items():
                add_dns_records(fqdn, ipaddr)

            # Add DNS infrastructure with multiple IPs per hostname
            for ns, ips in CACHING_NS.items():
                for ip in ips:
                    add_dns_records(ns, ip)
            for ns, ips in TOPLEVEL_NS.items():
                for ip in ips:
                    add_dns_records(ns, ip)
            for ns, ips in ROOT_NS.items():
                for ip in ips:
                    add_dns_records(ns, ip)

            # Add delegation NS records
            for domain, nameservers in delegations_fwd_dict.items():
                tld = self._get_tld(domain)
                if tld and tld in created_zones:
                    zone_file = os.path.join(tld_zd, f"{tld}.zone")
                    domain_without_tld = domain[:-len(tld)-1]
                    with open(zone_file, 'a') as f:
                        for ns in nameservers:
                            f.write(f"{domain_without_tld}\tNS\t{ns}.\n")

            for network, nameservers in delegations_rev_dict.items():
                net_parts = network.split('.')
                if len(net_parts) >= 3:
                    ip1 = net_parts[0]
                    if ip1 in created_zones:
                        rev_zone_file = os.path.join(tld_zd, f"{ip1}.zone")
                        with open(rev_zone_file, 'a') as f:
                            for ns in nameservers:
                                f.write(f"{net_parts[2]}.{net_parts[1]}\tNS\t{ns}.\n")

            # Add MX records
            for domain, mx_servers in domain_mx.items():
                tld = self._get_tld(domain)
                if tld and tld in created_zones:
                    zone_file = os.path.join(tld_zd, f"{tld}.zone")
                    domain_without_tld = domain[:-len(tld)-1]
                    with open(zone_file, 'a') as f:
                        for mx in mx_servers:
                            f.write(f"{domain_without_tld}\tMX\t10\t{mx}.\n")

            # Close named.conf
            with open(config.output_named_conf_path, 'a') as f:
                f.write("};\n")

            # Count zones created
            zones_created = len(created_zones)

            return DNSGenerationResult(
                success=True,
                zones_created=zones_created,
                hosts_processed=hosts_processed,
                hosts_skipped=hosts_skipped,
                warnings=warnings,
                errors=errors,
                output_files=[
                    config.output_dns_hosts_path,
                    config.output_named_conf_path,
                    root_zone_path
                ],
                message=f"Successfully generated DNS configuration with {zones_created} zones and {hosts_processed} hosts"
            )

        except Exception as e:
            return DNSGenerationResult(
                success=False,
                zones_created=0,
                hosts_processed=hosts_processed,
                hosts_skipped=hosts_skipped,
                warnings=warnings,
                errors=[str(e)],
                message=f"DNS generation failed: {str(e)}"
            )

    def _add_hosts_to_list(self, hosts_file: str, hosts_list: dict, domain_mx: dict,
                          delegations_fwd: dict, delegations_rev: dict,
                          is_mx: bool, warnings: list, quiet: bool) -> int:
        """Add hosts from file to hosts_list, checking delegations"""
        skipped = 0

        with open(hosts_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                ipaddr = parts[0]
                fqdn = parts[1]

                # Parse domain
                tld = self._get_tld(fqdn)
                sld = self._get_sld(fqdn)
                if not tld or not sld:
                    continue

                domain = f"{sld}.{tld}"

                # Check forward delegation
                if domain in delegations_fwd:
                    if not quiet:
                        warnings.append(f"Skipping host {fqdn} in delegated domain {domain}")
                    skipped += 1
                    continue

                # Check reverse delegation
                ip_network = '.'.join(ipaddr.split('.')[:3])
                if ip_network in delegations_rev:
                    if not quiet:
                        warnings.append(f"Skipping host {fqdn}: IP {ipaddr} in delegated network {ip_network}")
                    skipped += 1
                    continue

                # Add to hosts list
                hosts_list[fqdn] = ipaddr

                # Add to MX if needed
                if is_mx:
                    if domain not in domain_mx:
                        domain_mx[domain] = []
                    domain_mx[domain].append(fqdn)

        return skipped

    def _generate_dns_hosts_file(self, output_path: str):
        """Generate the DNS hosts file"""
        with open(output_path, 'w') as f:
            for ns, ips in CACHING_NS.items():
                for ip in ips:
                    f.write(f"{ip} {ns}\n")
            for ns, ips in TOPLEVEL_NS.items():
                for ip in ips:
                    f.write(f"{ip} {ns}\n")
            for ns, ips in ROOT_NS.items():
                for ip in ips:
                    f.write(f"{ip} {ns}\n")

    def _generate_named_conf(self, output_path: str, root_zd: str, tld_zd: str):
        """Generate named.conf file"""
        with open(output_path, 'w') as f:
            # ACLs
            f.write('acl "cache_addrs" {\n')
            for ns, ips in CACHING_NS.items():
                for ip in ips:
                    f.write(f'\t{ip}/32;        /* {ns} */\n')
            f.write('};\n\nacl "root_addrs" {\n')
            for ns, ips in ROOT_NS.items():
                for ip in ips:
                    f.write(f'\t{ip}/32;        /* {ns} */\n')
            f.write('};\n\nacl "tld_addrs" {\n')
            for ns, ips in TOPLEVEL_NS.items():
                for ip in ips:
                    f.write(f'\t{ip}/32;        /* {ns} */\n')
            f.write('};\n\n')

            # Options
            f.write('''options {
\tlisten-on port 53 { "cache_addrs"; "root_addrs"; "tld_addrs"; };
\tallow-query { any; };
\trecursion no;
\tcheck-names master ignore;
\tdirectory "/var/named";
\tdump-file "/var/named/data/cache_dump.db";
\tstatistics-file "/var/named/data/named_stats.txt";
\tmemstatistics-file "/var/named/data/named_mem_stats.txt";
\tpid-file "/run/named/named.pid";
\tsession-keyfile "/run/named/session.key";
};

logging {
\tchannel default_debug {
\t\tfile "data/named.run";
\t\tseverity dynamic;
\t\tprint-time yes;
\t};
};

view "caching" {
\tmatch-destinations { "cache_addrs"; };

\trecursion yes;
\tdnssec-validation no;

\tzone "." IN {
\t\ttype hint;
\t\tfile "/etc/topgen/named.root";
\t};
};

view "rootsrv" {
\tmatch-destinations { "root_addrs"; };

\tzone "." IN {
\t\ttype master;
\t\tfile "''' + os.path.join(root_zd, "root.zone") + '''";
\t\tallow-update { none; };
\t};
};

view "tldsrv" {
\tmatch-destinations { "tld_addrs"; };

''')

    def _generate_root_zone(self, output_path: str):
        """Generate root.zone file"""
        with open(output_path, 'w') as f:
            f.write('$TTL 300\n')
            f.write('$ORIGIN @\n')
            f.write('@ SOA a.root-servers.net. admin.step-fwd.net. (15061601 600 300 800 300)\n')

            # NS records
            for ns in ROOT_NS.keys():
                f.write(f'\t\t\tNS\t{ns}.\n')

            # A records (glue) for root servers
            for ns, ips in ROOT_NS.items():
                for ip in ips:
                    f.write(f'{ns}.\tA\t{ip}\n')

            # in-addr.arpa delegation
            f.write(';\n; in-game reverse DNS is also handled by the tld servers:\n;\n')
            for ns in TOPLEVEL_NS.keys():
                f.write(f'in-addr.arpa.\t\tNS\t{ns}.\n')

            # TLD servers glue
            for ns, ips in TOPLEVEL_NS.items():
                for ip in ips:
                    f.write(f'{ns}.\tA\t{ip}\n')

            # Caching nameservers (public resolvers)
            f.write(';\n; public caching nameservers:\n;\n')
            for ns, ips in CACHING_NS.items():
                for ip in ips:
                    f.write(f'{ns}.\tA\t{ip}\n')

            f.write(';\n; begin root zone data here:\n;\n')

    def _get_tld_zone_header(self) -> str:
        """Get header for TLD zone files"""
        header = '$TTL 300\n$ORIGIN @\n'
        header += '@ SOA ns.level3.net. admin.step-fwd.net. (15061601 600 300 800 300)\n'

        for ns in TOPLEVEL_NS.keys():
            header += f'\t\t\tNS\t{ns}.\n'

        for ns, ips in TOPLEVEL_NS.items():
            for ip in ips:
                header += f'{ns}.\tA\t{ip}\n'

        header += ';\n; begin zone data here:\n;\n'
        return header

    def _create_forward_zone(self, tld: str, tld_zd: str, named_conf_path: str, root_zone_path: str):
        """Create a forward zone file"""
        zone_file = os.path.join(tld_zd, f"{tld}.zone")

        if not os.path.exists(zone_file):
            # Write zone file
            with open(zone_file, 'w') as f:
                f.write(self._get_tld_zone_header())

            # Add to named.conf
            with open(named_conf_path, 'a') as f:
                f.write(f'\tzone "{tld}" IN {{\n')
                f.write(f'\t\ttype master;\n')
                f.write(f'\t\tfile "{zone_file}";\n')
                f.write(f'\t\tallow-update {{ none; }};\n')
                f.write(f'\t}};\n')

            # Add NS delegation to root.zone
            with open(root_zone_path, 'a') as f:
                for ns in TOPLEVEL_NS.keys():
                    f.write(f'{tld}.\tNS\t{ns}\n')

    def _create_reverse_zone(self, ip1: str, tld_zd: str, named_conf_path: str):
        """Create a reverse zone file"""
        zone_file = os.path.join(tld_zd, f"{ip1}.zone")

        if not os.path.exists(zone_file):
            # Write zone file
            with open(zone_file, 'w') as f:
                f.write(self._get_tld_zone_header())

            # Add to named.conf
            with open(named_conf_path, 'a') as f:
                f.write(f'\tzone "{ip1}.in-addr.arpa." IN {{\n')
                f.write(f'\t\ttype master;\n')
                f.write(f'\t\tfile "{zone_file}";\n')
                f.write(f'\t\tallow-update {{ none; }};\n')
                f.write(f'\t}};\n')

    def _get_zone_info(self, filename: str, filepath: str, zone_type: str) -> DNSZoneInfo:
        """Get information about a zone file"""
        name = filename.replace(".zone", "")
        size_bytes = os.path.getsize(filepath)
        modified = datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()

        # Count records
        record_count = 0
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(';') and not line.startswith('$'):
                        record_count += 1
        except:
            pass

        return DNSZoneInfo(
            name=name,
            type=zone_type,
            path=filepath,
            record_count=record_count,
            size_bytes=size_bytes,
            modified=modified
        )

    def _get_tld(self, fqdn: str) -> Optional[str]:
        """Extract TLD from FQDN"""
        parts = fqdn.split('.')
        if len(parts) >= 2:
            return parts[-1]
        return None

    def _get_sld(self, fqdn: str) -> Optional[str]:
        """Extract second-level domain from FQDN"""
        parts = fqdn.split('.')
        if len(parts) >= 2:
            return parts[-2]
        return None

    def _check_needs_regeneration(self, config: DNSConfiguration, vhost_hosts: List[DNSHostsFile]) -> bool:
        """Check if DNS configuration needs to be regenerated by comparing file modification times

        Returns True if any source configuration file is newer than the generated named.conf,
        indicating that the user needs to regenerate DNS configuration.
        """
        try:
            # If named.conf doesn't exist, configuration hasn't been generated yet
            if not os.path.exists(config.output_named_conf_path):
                return False  # Not configured yet, so no "regeneration" needed

            # Get the modification time of the generated named.conf
            named_conf_mtime = os.path.getmtime(config.output_named_conf_path)

            # Check if any source files are newer than named.conf

            # Check vhost hosts files
            for vhost in vhost_hosts:
                if os.path.exists(vhost.path):
                    if os.path.getmtime(vhost.path) > named_conf_mtime:
                        return True

            # Check backbone hosts
            if config.backbone_hosts_path and os.path.exists(config.backbone_hosts_path):
                if os.path.getmtime(config.backbone_hosts_path) > named_conf_mtime:
                    return True

            # Check custom hosts
            if os.path.exists(config.custom_hosts_path):
                if os.path.getmtime(config.custom_hosts_path) > named_conf_mtime:
                    return True

            # Check mail hosts
            if config.mail_hosts_path and os.path.exists(config.mail_hosts_path):
                if os.path.getmtime(config.mail_hosts_path) > named_conf_mtime:
                    return True

            # Check delegations
            if os.path.exists(config.delegations_path):
                if os.path.getmtime(config.delegations_path) > named_conf_mtime:
                    return True

            # Check extra hosts
            for extra_path in config.extra_hosts_paths:
                if os.path.exists(extra_path):
                    if os.path.getmtime(extra_path) > named_conf_mtime:
                        return True

            return False

        except Exception:
            # On error, don't show warning
            return False

    def _validate_ip(self, ip: str) -> bool:
        """Validate IP address format"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False

        try:
            for part in parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        except ValueError:
            return False

    def _validate_fqdn(self, fqdn: str) -> bool:
        """Validate FQDN format"""
        # Simple validation: check for valid characters and structure
        if not fqdn or len(fqdn) > 253:
            return False

        # Must have at least one dot (domain.tld)
        if '.' not in fqdn:
            return False

        # Check each label
        labels = fqdn.split('.')
        for label in labels:
            if not label or len(label) > 63:
                return False
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
                return False

        return True
