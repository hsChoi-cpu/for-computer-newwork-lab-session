\# Task 2 Report — Where Exactly Are You on the Internet?



\## Part A — Campus Wi-Fi



\### A1. Interface address and subnet mask



The campus Wi-Fi interface had the following configuration:



\- IPv4 address: `172.16.24.142`

\- Subnet mask: `255.255.255.0`

\- CIDR prefix: `/24`

\- Default gateway: `172.16.24.1`

\- Public IPv4 address seen from outside: `163.152.233.24`



\### A2. Subnet range



With subnet mask `255.255.255.0`, the address belongs to the network:



`172.16.24.0/24`



The subnet range is:



\- Network address: `172.16.24.0`

\- First usable address: `172.16.24.1`

\- Last usable address: `172.16.24.254`

\- Broadcast address: `172.16.24.255`



This result also matches the output of Task 1 `network\_range("172.16.24.0/24")`.



\### A3. Default gateway



The default gateway is `172.16.24.1`, which is inside the usable host range of the subnet.



The gateway must normally be reachable on the same local subnet because the host needs to send frames directly to the gateway when forwarding packets to destinations outside the local network.



\### A4. Public address



The public IPv4 address observed from outside was:



`163.152.233.24`



This is different from the local interface address `172.16.24.142`.



\### A5. NAT analysis



The local address `172.16.24.142` is an RFC 1918 private address because it is inside `172.16.0.0/12`.



The outside address `163.152.233.24` is public. Since the private and public addresses differ, the connection is behind at least one layer of NAT.



From the host-side information alone, it is not possible to prove whether there is exactly one NAT layer or more than one. To distinguish one layer from two, the WAN-side address of the intermediate router would need to be checked. If the router's WAN address is itself private or belongs to the CGNAT range `100.64.0.0/10` while the outside address is different, then another NAT layer exists upstream.



\---



\## Part B — Comparison with Tethering



The tethering interface had the following configuration:



\- IPv4 address: `10.222.13.209`

\- Subnet mask: `255.255.255.0`

\- CIDR prefix: `/24`

\- Default gateway: `10.222.13.184`

\- Public IPv4 address seen from outside: `163.152.233.25`



Its subnet is:



`10.222.13.0/24`



with:



\- First usable address: `10.222.13.1`

\- Last usable address: `10.222.13.254`

\- Broadcast address: `10.222.13.255`



The gateway `10.222.13.184` is inside this subnet.



\### B3. What changed between the two networks?



| Item | Campus Wi-Fi | Tethering |

|---|---|---|

| Private IPv4 | `172.16.24.142` | `10.222.13.209` |

| Subnet mask | `255.255.255.0` | `255.255.255.0` |

| Default gateway | `172.16.24.1` | `10.222.13.184` |

| Public IPv4 | `163.152.233.24` | `163.152.233.25` |



The private IPv4 address changed because the two networks use different local addressing and DHCP environments. Each network assigned an address from its own private subnet.



The subnet mask did not change; both networks used `/24`.



The default gateway changed because each network uses a different local router.



The public IPv4 address also changed, from `163.152.233.24` to `163.152.233.25`, which means the externally visible NAT address was different between the two measurements.



Both local addresses are private RFC 1918 addresses, so both connections are behind at least one NAT layer.



\---



\## Part C — DHCP Capture



The DHCP exchange was captured successfully and contained all four DORA messages:



1\. Discover

2\. Offer

3\. Request

4\. ACK



\### C2. Discover source and destination



The DHCP Discover packet had:



\- Source address: `0.0.0.0`

\- Destination address: `255.255.255.255`



The source address is `0.0.0.0` because the client has not yet been assigned a valid IPv4 address when it sends the Discover message.



The destination is the limited broadcast address `255.255.255.255` because the client does not yet know which DHCP server will provide an address.



\### C3. Lease time



The DHCP lease time offered by the server was:



`3600 seconds`, or `1 hour`.



At approximately half of the lease time, around `1800 seconds` or `30 minutes`, the client normally begins trying to renew the lease.



\### C4. Discover and ACK delivery



The DHCP ACK packet had:



\- Source address: `10.222.13.184`

\- Destination address: `255.255.255.255`



The Discover message had to be broadcast because the client did not yet have a valid IP address and did not know the DHCP server.



By the ACK stage, the server already knows the client and the IP address being assigned, so an ACK can in some cases be sent by unicast.



However, in this capture the ACK was still sent to `255.255.255.255`, so this particular exchange used broadcast for the ACK as well. The important change is that unicast becomes possible after the server knows the client and the assigned address, even though this captured ACK remained broadcast.

