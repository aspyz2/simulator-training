"""
Inject drag_items / drag_categories / drag_answers into every drag_drop question.
Run once: python build_dragdrop.py
"""
import json

MANUAL = {
    # ── already correct ───────────────────────────────────────────────────────
    22: None,   # keep existing

    # ── IPv6 address types ────────────────────────────────────────────────────
    26: {
        'drag_categories': ['Global Unicast', 'Unique Local', 'Link-Local', 'Multicast'],
        'drag_items': [
            '2001:db8:600d:cafe::123', '3ffe:e54d:620:a87a::f00d',
            'Fcba:926a:e8e:7a25:c6d2:e8e7',
            'fe80::b:b::4',
            'ff02::1', 'ff02::2',
        ],
        'drag_answers': {
            '2001:db8:600d:cafe::123': 'Global Unicast',
            '3ffe:e54d:620:a87a::f00d': 'Global Unicast',
            'Fcba:926a:e8e:7a25:c6d2:e8e7': 'Unique Local',
            'fe80::b:b::4': 'Link-Local',
            'ff02::1': 'Multicast',
            'ff02::2': 'Multicast',
        },
    },

    # ── TCP vs UDP ─────────────────────────────────────────────────────────────
    46: {
        'drag_categories': ['TCP', 'UDP'],
        'drag_items': [
            'Used to reliably share files between devices',
            'Supports reliable data transmission',
            'Appropriate for real-time streaming',
            'Not connection-oriented',
        ],
        'drag_answers': {
            'Used to reliably share files between devices': 'TCP',
            'Supports reliable data transmission': 'TCP',
            'Appropriate for real-time streaming': 'UDP',
            'Not connection-oriented': 'UDP',
        },
    },

    # ── Node identifiers (no image — generic network parameters) ──────────────
    48: {
        'drag_categories': ['IP Address', 'Subnet Mask', 'Default Gateway', 'DNS Server'],
        'drag_items': [
            '192.168.1.100', '255.255.255.0', '192.168.1.1', '8.8.8.8',
        ],
        'drag_answers': {
            '192.168.1.100': 'IP Address',
            '255.255.255.0': 'Subnet Mask',
            '192.168.1.1': 'Default Gateway',
            '8.8.8.8': 'DNS Server',
        },
    },

    # ── TCP vs UDP ─────────────────────────────────────────────────────────────
    79: {
        'drag_categories': ['TCP', 'UDP'],
        'drag_items': [
            'Uses a three-way handshake',
            'Provides a reliable connection',
            'Preferred for web browsing',
            'Faster data transmission',
            'Connectionless protocol',
            'Used for streaming',
        ],
        'drag_answers': {
            'Uses a three-way handshake': 'TCP',
            'Provides a reliable connection': 'TCP',
            'Preferred for web browsing': 'TCP',
            'Faster data transmission': 'UDP',
            'Connectionless protocol': 'UDP',
            'Used for streaming': 'UDP',
        },
    },
    80: {
        'drag_categories': ['TCP', 'UDP'],
        'drag_items': [
            'Sends data in a specific order',
            'Requires an established connection',
            'Supports web browsing',
            'Suited for live streaming',
            'Retransmission is unsupported',
            'Tolerates packet loss',
        ],
        'drag_answers': {
            'Sends data in a specific order': 'TCP',
            'Requires an established connection': 'TCP',
            'Supports web browsing': 'TCP',
            'Suited for live streaming': 'UDP',
            'Retransmission is unsupported': 'UDP',
            'Tolerates packet loss': 'UDP',
        },
    },

    # ── Access / Distribution / Core layers ───────────────────────────────────
    81: {
        'drag_categories': ['Access', 'Distribution', 'Core'],
        'drag_items': [
            'Provides end-user device connectivity',
            'Implemented as top-of-rack switches in spine-leaf',
            'Provides routing, filtering, and WAN access',
            'Aggregates access-layer connections',
            'Switches packets as fast as possible',
            'Responsible for high-speed packet switching',
        ],
        'drag_answers': {
            'Provides end-user device connectivity': 'Access',
            'Implemented as top-of-rack switches in spine-leaf': 'Access',
            'Provides routing, filtering, and WAN access': 'Distribution',
            'Aggregates access-layer connections': 'Distribution',
            'Switches packets as fast as possible': 'Core',
            'Responsible for high-speed packet switching': 'Core',
        },
    },

    # ── TCP vs UDP ─────────────────────────────────────────────────────────────
    83: {
        'drag_categories': ['TCP', 'UDP'],
        'drag_items': [
            'Connection-oriented protocol',
            'Verifies delivery and retransmits lost packets',
            'Does not guarantee delivery or order',
            'Efficient for real-time applications like VoIP',
            'Supports broadcast and multicast traffic',
        ],
        'drag_answers': {
            'Connection-oriented protocol': 'TCP',
            'Verifies delivery and retransmits lost packets': 'TCP',
            'Does not guarantee delivery or order': 'UDP',
            'Efficient for real-time applications like VoIP': 'UDP',
            'Supports broadcast and multicast traffic': 'UDP',
        },
    },

    # ── IPv6 address types ────────────────────────────────────────────────────
    85: {
        'drag_categories': ['Link-Local Unicast', 'Multicast', 'Global Unicast'],
        'drag_items': [
            'fe80:f047:ccc4:3533:531f:4aea:924e:7',
            'ff00:e586:4270:41ee:9ccd:6a31:19d4:12',
            '2001:db8:600d:cafe::1',
        ],
        'drag_answers': {
            'fe80:f047:ccc4:3533:531f:4aea:924e:7': 'Link-Local Unicast',
            'ff00:e586:4270:41ee:9ccd:6a31:19d4:12': 'Multicast',
            '2001:db8:600d:cafe::1': 'Global Unicast',
        },
    },

    # ── IPv6 address characteristics ──────────────────────────────────────────
    87: {
        'drag_categories': ['Multicast', 'Unicast', 'Broadcast'],
        'drag_items': [
            'Provides one-to-many communications',
            'Sends packets to a group address',
            'One-to-one communications',
            'One-to-all communications',
        ],
        'drag_answers': {
            'Provides one-to-many communications': 'Multicast',
            'Sends packets to a group address': 'Multicast',
            'One-to-one communications': 'Unicast',
            'One-to-all communications': 'Broadcast',
        },
    },

    # ── Cable types ───────────────────────────────────────────────────────────
    90: {
        'drag_categories': ['Copper', 'Fiber-Optic'],
        'drag_items': [
            'Comprised of shielded and unshielded twisted pairs',
            'Contains a conductor, bedding, and sheath',
            'Susceptible to electromagnetic interference',
            'Uses light signals for data transmission',
            'Immune to electromagnetic interference',
            'Supports longer distances',
        ],
        'drag_answers': {
            'Comprised of shielded and unshielded twisted pairs': 'Copper',
            'Contains a conductor, bedding, and sheath': 'Copper',
            'Susceptible to electromagnetic interference': 'Copper',
            'Uses light signals for data transmission': 'Fiber-Optic',
            'Immune to electromagnetic interference': 'Fiber-Optic',
            'Supports longer distances': 'Fiber-Optic',
        },
    },

    # ── Management methods ────────────────────────────────────────────────────
    100: {
        'drag_categories': ['Telnet', 'SSH', 'Console', 'HTTPS'],
        'drag_items': [
            'Supports clear-text connections to the controller CLI',
            'Supports encrypted access to CLI',
            'Supports a secure channel for data transfer',
            'Supports physical connections over a serial cable',
            'Supports secure web access for management',
        ],
        'drag_answers': {
            'Supports clear-text connections to the controller CLI': 'Telnet',
            'Supports encrypted access to CLI': 'SSH',
            'Supports a secure channel for data transfer': 'SSH',
            'Supports physical connections over a serial cable': 'Console',
            'Supports secure web access for management': 'HTTPS',
        },
    },

    # ── Network topology layers (no explanation — generic) ────────────────────
    161: {
        'drag_categories': ['Access', 'Distribution', 'Core'],
        'drag_items': [
            'Connects workstations and end devices',
            'Provides port security',
            'Provides routing between VLANs',
            'Enforces network policy',
            'High-speed backbone interconnection',
            'Provides fast packet forwarding',
        ],
        'drag_answers': {
            'Connects workstations and end devices': 'Access',
            'Provides port security': 'Access',
            'Provides routing between VLANs': 'Distribution',
            'Enforces network policy': 'Distribution',
            'High-speed backbone interconnection': 'Core',
            'Provides fast packet forwarding': 'Core',
        },
    },

    # ── Access Point vs WLC ───────────────────────────────────────────────────
    239: {
        'drag_categories': ['Access Point', 'Wireless LAN Controller'],
        'drag_items': [
            'Transmits and receives radio signals',
            'Configurable as a workgroup bridge',
            'Uses templates to implement QoS configuration',
            'Supplies user connection data within a device group',
        ],
        'drag_answers': {
            'Transmits and receives radio signals': 'Access Point',
            'Configurable as a workgroup bridge': 'Access Point',
            'Uses templates to implement QoS configuration': 'Wireless LAN Controller',
            'Supplies user connection data within a device group': 'Wireless LAN Controller',
        },
    },

    # ── Subnet mask matching ───────────────────────────────────────────────────
    269: {
        'drag_categories': ['255.255.255.128', '255.255.255.240', '255.255.255.248', '255.255.255.252'],
        'drag_items': [
            '10.10.13.0/25', '10.10.13.128/28', '10.10.13.160/29', '10.10.13.252/30',
        ],
        'drag_answers': {
            '10.10.13.0/25': '255.255.255.128',
            '10.10.13.128/28': '255.255.255.240',
            '10.10.13.160/29': '255.255.255.248',
            '10.10.13.252/30': '255.255.255.252',
        },
    },

    # ── IPv6 address types ────────────────────────────────────────────────────
    271: {
        'drag_categories': ['Global Unicast', 'Unique Local'],
        'drag_items': [
            'Equivalent to public IPv4 addresses',
            'Routable and reachable via the Internet',
            'Addresses with prefix FC00::/7',
            'For exclusive use internally without Internet routing',
        ],
        'drag_answers': {
            'Equivalent to public IPv4 addresses': 'Global Unicast',
            'Routable and reachable via the Internet': 'Global Unicast',
            'Addresses with prefix FC00::/7': 'Unique Local',
            'For exclusive use internally without Internet routing': 'Unique Local',
        },
    },

    # ── Subnet mask matching ───────────────────────────────────────────────────
    282: {
        'drag_categories': ['255.255.255.240', '255.255.255.224', '255.255.255.128', '255.255.255.248', '255.255.254.0'],
        'drag_items': [
            '172.16.3.128', '172.16.3.64', '172.16.2.128', '172.16.3.192', '172.16.4.0',
        ],
        'drag_answers': {
            '172.16.3.128': '255.255.255.240',
            '172.16.3.64': '255.255.255.224',
            '172.16.2.128': '255.255.255.128',
            '172.16.3.192': '255.255.255.248',
            '172.16.4.0': '255.255.254.0',
        },
    },

    # ── Routing protocols to routes ───────────────────────────────────────────
    310: {
        'drag_categories': ['Static', 'EIGRP', 'OSPF', 'RIP'],
        'drag_items': [
            '207.164.200.244/30', '192.168.2.0/24', '192.168.1.0/24', '172.16.2.0/24',
        ],
        'drag_answers': {
            '207.164.200.244/30': 'Static',
            '192.168.2.0/24': 'EIGRP',
            '192.168.1.0/24': 'OSPF',
            '172.16.2.0/24': 'RIP',
        },
    },

    # ── Routing table components ──────────────────────────────────────────────
    317: {
        'drag_categories': ['SP', 'AD', 'M'],
        'drag_items': ['/29', '90', '40'],
        'drag_answers': {'/29': 'SP', '90': 'AD', '40': 'M'},
    },

    # ── TCP vs UDP ─────────────────────────────────────────────────────────────
    321: {
        'drag_categories': ['TCP', 'UDP'],
        'drag_items': [
            'Uses sequence numbers',
            'Relies on acknowledgment packets',
            'Ensures data integrity',
            'Supports real-time applications',
            'Connectionless at transport layer',
            'Minimal error checking',
        ],
        'drag_answers': {
            'Uses sequence numbers': 'TCP',
            'Relies on acknowledgment packets': 'TCP',
            'Ensures data integrity': 'TCP',
            'Supports real-time applications': 'UDP',
            'Connectionless at transport layer': 'UDP',
            'Minimal error checking': 'UDP',
        },
    },
    329: {
        'drag_categories': ['TCP', 'UDP'],
        'drag_items': [
            'Optimizes transmission rates to receiver',
            'Controls connections between sender and receiver',
            'Guarantees packet delivery',
            'Capable of sending multicast transmissions',
            'Transmits live and real-time data',
            'Reduces end-to-end delays',
        ],
        'drag_answers': {
            'Optimizes transmission rates to receiver': 'TCP',
            'Controls connections between sender and receiver': 'TCP',
            'Guarantees packet delivery': 'TCP',
            'Capable of sending multicast transmissions': 'UDP',
            'Transmits live and real-time data': 'UDP',
            'Reduces end-to-end delays': 'UDP',
        },
    },

    # ── DHCP components ───────────────────────────────────────────────────────
    467: {
        'drag_categories': ['DHCP Server', 'Snooping Binding Database', 'Spurious DHCP Server'],
        'drag_items': [
            'Propagates IP addresses to hosts on the network',
            'List of hosts on the network',
            'Unknown to the administrative domain',
            'Unknown DHCP server within the domain',
        ],
        'drag_answers': {
            'Propagates IP addresses to hosts on the network': 'DHCP Server',
            'List of hosts on the network': 'Snooping Binding Database',
            'Unknown to the administrative domain': 'Snooping Binding Database',
            'Unknown DHCP server within the domain': 'Spurious DHCP Server',
        },
    },

    # ── TCP vs UDP ─────────────────────────────────────────────────────────────
    490: {
        'drag_categories': ['TCP', 'UDP'],
        'drag_items': [
            'Acknowledgement mechanism',
            'Guaranteed transmission',
            'Low overhead',
            'Connectionless',
        ],
        'drag_answers': {
            'Acknowledgement mechanism': 'TCP',
            'Guaranteed transmission': 'TCP',
            'Low overhead': 'UDP',
            'Connectionless': 'UDP',
        },
    },

    # ── AAA ───────────────────────────────────────────────────────────────────
    527: {
        'drag_categories': ['Authentication', 'Authorization', 'Accounting'],
        'drag_items': [
            'Validates user credentials',
            'Verifies identity before granting access',
            'Grants access to network assets such as FTP servers',
            'Limits CLI commands a user can perform',
            'Records the duration of each connection',
            'Provides access reporting',
        ],
        'drag_answers': {
            'Validates user credentials': 'Authentication',
            'Verifies identity before granting access': 'Authentication',
            'Grants access to network assets such as FTP servers': 'Authorization',
            'Limits CLI commands a user can perform': 'Authorization',
            'Records the duration of each connection': 'Accounting',
            'Provides access reporting': 'Accounting',
        },
    },

    # ── Router config sequence (no image — generic enable secret) ─────────────
    546: {
        'drag_categories': ['Step 1', 'Step 2', 'Step 3'],
        'drag_items': [
            'enable', 'configure terminal', 'enable secret <password>',
        ],
        'drag_answers': {
            'enable': 'Step 1',
            'configure terminal': 'Step 2',
            'enable secret <password>': 'Step 3',
        },
    },

    # ── WLAN security layers ──────────────────────────────────────────────────
    550: {
        'drag_categories': ['Layer 2 Security', 'Layer 3 Security'],
        'drag_items': [
            'WPA + WPA2', '802.1X', 'Static WEP', 'CKIP',
            'IPSec', 'VPN Pass-Through', 'Web Policy', 'Web Passthrough',
        ],
        'drag_answers': {
            'WPA + WPA2': 'Layer 2 Security',
            '802.1X': 'Layer 2 Security',
            'Static WEP': 'Layer 2 Security',
            'CKIP': 'Layer 2 Security',
            'IPSec': 'Layer 3 Security',
            'VPN Pass-Through': 'Layer 3 Security',
            'Web Policy': 'Layer 3 Security',
            'Web Passthrough': 'Layer 3 Security',
        },
    },

    # ── Authentication types ──────────────────────────────────────────────────
    556: {
        'drag_categories': ['Biometrics', 'Certificates', 'Multifactor Authentication'],
        'drag_items': [
            'Relies on physical characteristics such as fingerprints',
            'Something you are',
            'Digital credentials used for authentication',
            'Can be revoked if compromised',
            'Requires at least two different authentication factors',
            'Commonly uses one-time passwords (OTPs)',
        ],
        'drag_answers': {
            'Relies on physical characteristics such as fingerprints': 'Biometrics',
            'Something you are': 'Biometrics',
            'Digital credentials used for authentication': 'Certificates',
            'Can be revoked if compromised': 'Certificates',
            'Requires at least two different authentication factors': 'Multifactor Authentication',
            'Commonly uses one-time passwords (OTPs)': 'Multifactor Authentication',
        },
    },

    # ── VLAN attack mitigations ───────────────────────────────────────────────
    558: {
        'drag_categories': ['MAC Flooding', '802.1Q Double-Tagging', 'Switch Spoofing'],
        'drag_items': [
            'Configure port security',
            'Configure DHCP snooping',
            'Configure native VLAN with a nondefault VLAN ID',
            'Disable Dynamic Trunking Protocol',
        ],
        'drag_answers': {
            'Configure port security': 'MAC Flooding',
            'Configure DHCP snooping': 'MAC Flooding',
            'Configure native VLAN with a nondefault VLAN ID': '802.1Q Double-Tagging',
            'Disable Dynamic Trunking Protocol': 'Switch Spoofing',
        },
    },

    # ── AAA ───────────────────────────────────────────────────────────────────
    598: {
        'drag_categories': ['Authentication', 'Authorization'],
        'drag_items': [
            'Validates user credentials',
            'Secures access to routers',
            "Limits the user's access permissions",
            'Allows the user to change to enable mode',
        ],
        'drag_answers': {
            'Validates user credentials': 'Authentication',
            'Secures access to routers': 'Authentication',
            "Limits the user's access permissions": 'Authorization',
            'Allows the user to change to enable mode': 'Authorization',
        },
    },
    612: {
        'drag_categories': ['Authentication', 'Authorization'],
        'drag_items': [
            'Uses a RADIUS server to allow user access',
            'Verifies the user before granting access',
            'Determines what resources or commands a user can access',
            'Limits CLI commands a user can use',
        ],
        'drag_answers': {
            'Uses a RADIUS server to allow user access': 'Authentication',
            'Verifies the user before granting access': 'Authentication',
            'Determines what resources or commands a user can access': 'Authorization',
            'Limits CLI commands a user can use': 'Authorization',
        },
    },
    616: {
        'drag_categories': ['Authentication', 'Authorization'],
        'drag_items': [
            'Performs user validation via TACACS+',
            'Verifies who you are',
            'Restricts access to FTP servers',
            'Limits CLI commands a user can perform',
        ],
        'drag_answers': {
            'Performs user validation via TACACS+': 'Authentication',
            'Verifies who you are': 'Authentication',
            'Restricts access to FTP servers': 'Authorization',
            'Limits CLI commands a user can perform': 'Authorization',
        },
    },
    619: {
        'drag_categories': ['Accounting', 'Authorization'],
        'drag_items': [
            'Records the amount of network resources consumed',
            'Tracks the services used',
            'Defines what actions and permissions a user is allowed',
            'Limits CLI commands a user can perform',
        ],
        'drag_answers': {
            'Records the amount of network resources consumed': 'Accounting',
            'Tracks the services used': 'Accounting',
            'Defines what actions and permissions a user is allowed': 'Authorization',
            'Limits CLI commands a user can perform': 'Authorization',
        },
    },

    # ── Automation tools ──────────────────────────────────────────────────────
    627: {
        'drag_categories': ['Ansible', 'Puppet'],
        'drag_items': [
            'Executes modules via SSH by default',
            'Uses the YAML language',
            'Operates without agents (agentless)',
            'Uses a pull model by default',
            'Uses a domain-specific language (DSL)',
        ],
        'drag_answers': {
            'Executes modules via SSH by default': 'Ansible',
            'Uses the YAML language': 'Ansible',
            'Operates without agents (agentless)': 'Ansible',
            'Uses a pull model by default': 'Puppet',
            'Uses a domain-specific language (DSL)': 'Puppet',
        },
    },

    # ── AAA ───────────────────────────────────────────────────────────────────
    667: {
        'drag_categories': ['Accounting', 'Authentication', 'Authorization'],
        'drag_items': ['Tracks activity', 'Verifies identity', 'Verifies access rights'],
        'drag_answers': {
            'Tracks activity': 'Accounting',
            'Verifies identity': 'Authentication',
            'Verifies access rights': 'Authorization',
        },
    },

    # ── DNA Center vs Traditional ─────────────────────────────────────────────
    665: {
        'drag_categories': ['Cisco DNA Center', 'Traditional Device Management'],
        'drag_items': [
            'Monitors the cloud for software updates',
            'Uses CLI templates to apply consistent configuration to multiple devices',
            'Uses Netflow to analyze potential security threats',
            'Implements changes via an SSH terminal',
            'Manages device configurations on a per-device basis',
            'Security managed near perimeter with firewalls and VPNs',
        ],
        'drag_answers': {
            'Monitors the cloud for software updates': 'Cisco DNA Center',
            'Uses CLI templates to apply consistent configuration to multiple devices': 'Cisco DNA Center',
            'Uses Netflow to analyze potential security threats': 'Cisco DNA Center',
            'Implements changes via an SSH terminal': 'Traditional Device Management',
            'Manages device configurations on a per-device basis': 'Traditional Device Management',
            'Security managed near perimeter with firewalls and VPNs': 'Traditional Device Management',
        },
    },

    # ── Controller-Based vs Traditional ──────────────────────────────────────
    674: {
        'drag_categories': ['Controller-Based Networking', 'Traditional Networking'],
        'drag_items': [
            'Allows better control over how networks are configured',
            'Uses a centralized control plane',
            'Requires a distributed control plane',
            'New devices configured using physical infrastructure',
        ],
        'drag_answers': {
            'Allows better control over how networks are configured': 'Controller-Based Networking',
            'Uses a centralized control plane': 'Controller-Based Networking',
            'Requires a distributed control plane': 'Traditional Networking',
            'New devices configured using physical infrastructure': 'Traditional Networking',
        },
    },
    678: {
        'drag_categories': ['Controller-Based Networking', 'Traditional Networking'],
        'drag_items': [
            'Leverages SDN controllers',
            'Provides a centralized network view',
            'Higher scalability with automation',
            'Each device manages its own control plane',
            'Configuration done per device via CLI',
        ],
        'drag_answers': {
            'Leverages SDN controllers': 'Controller-Based Networking',
            'Provides a centralized network view': 'Controller-Based Networking',
            'Higher scalability with automation': 'Controller-Based Networking',
            'Each device manages its own control plane': 'Traditional Networking',
            'Configuration done per device via CLI': 'Traditional Networking',
        },
    },
    705: {
        'drag_categories': ['Controller-Based Networking', 'Traditional Networking'],
        'drag_items': [
            'Leverages controllers to handle network management',
            'Provides better control over network policies',
            'Higher maintenance costs',
            'Provides a centralized view of the network',
        ],
        'drag_answers': {
            'Leverages controllers to handle network management': 'Controller-Based Networking',
            'Provides better control over network policies': 'Controller-Based Networking',
            'Higher maintenance costs': 'Traditional Networking',
            'Provides a centralized view of the network': 'Traditional Networking',
        },
    },

    # ── SDN planes ───────────────────────────────────────────────────────────
    708: {
        'drag_categories': ['Northbound API', 'Southbound API'],
        'drag_items': [
            'Supports automation',
            'Communicates between the SDN controller and the application plane',
            'Supports interaction between the network controller and network devices',
            'Communicates between the SDN controller and network devices',
        ],
        'drag_answers': {
            'Supports automation': 'Northbound API',
            'Communicates between the SDN controller and the application plane': 'Northbound API',
            'Supports interaction between the network controller and network devices': 'Southbound API',
            'Communicates between the SDN controller and network devices': 'Southbound API',
        },
    },
}


def main():
    with open('questions.json', encoding='utf-8') as f:
        qs = json.load(f)

    updated, skipped = 0, 0

    for q in qs:
        if q.get('type') != 'drag_drop':
            continue

        qid = q['id']

        if qid not in MANUAL:
            print(f'Q{qid}: NO OVERRIDE — left as-is')
            skipped += 1
            continue

        data = MANUAL[qid]
        if data is None:
            print(f'Q{qid}: SKIP (keep existing)')
            continue

        q['drag_categories'] = data['drag_categories']
        q['drag_items']      = data['drag_items']
        q['drag_answers']    = data['drag_answers']
        updated += 1
        print(f'Q{qid}: OK  cats={data["drag_categories"]}  items={len(data["drag_items"])}')

    with open('questions.json', 'w', encoding='utf-8') as f:
        json.dump(qs, f, ensure_ascii=False, indent=2)

    print(f'\nDone. Updated={updated}  Skipped={skipped}')


if __name__ == '__main__':
    main()
