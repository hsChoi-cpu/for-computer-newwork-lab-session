\# Week 5 Observation



\## Task 1

`/31`은 두 주소를 모두 사용 가능하게, `/32`는 단일 주소 자체를 사용 가능하게 처리했다. `10.20.30.70`은 `/8`, `/16`, `/24`, `/26` 네 항목에 모두 일치했으며 Longest-Prefix Match에 따라 `/26`의 `lab-rack-2`가 선택되었다. 동일 prefix 길이가 겹치면 먼저 등록된 항목을 유지했다.



\## Task 2

Campus Wi-Fi와 tethering 모두 사설 IP와 외부 공인 IP가 달라 최소 한 단계의 NAT를 거친다. 두 네트워크에서 사설 IP, 게이트웨이, 공인 IP가 모두 달라졌고, DHCP Discover는 아직 IP가 없기 때문에 `0.0.0.0`에서 `255.255.255.255`로 broadcast되었다.



\## Task 3

Prefix 길이별 dictionary를 사용해 route를 저장했으며 메모리 사용량은 `O(N)`이다. Lookup은 전체 route 수가 아니라 존재하는 prefix 길이 수에 비례하며, `0.009초`, `2761.8배` 향상, 오답 0으로 `strong`을 달성했다. 하드웨어에는 bitwise trie가 적합하지만 Python에서는 최적화된 dictionary가 더 빠르게 동작했다.

