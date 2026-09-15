# Week 3 Observation



## Task 1 — Iterative DNS Resolver



루트 서버는 모든 도메인의 최종 IP를 저장하지 않습니다. 대신 .kr 같은 최상위 도메인(TLD)을 담당하는 DNS 서버 정보를 반환해 관리 책임을 위임합니다. 따라서 루트 → .kr 서버 → korea.ac.kr 권한 서버 순으로 찾아야합니다.


delegation에 glue A 레코드가 없으면, NS 이름 자체를 별도의 반복 DNS 조회로 해석해 IP 주소를 구한 뒤 그 NS 서버에 질의하도록 구현했습니다. 이번 www.korea.ac.kr 조회에서는 glue가 제공되었으므로 추가 lookup은 0회였습니다.


www.korea.ac.kr 조회에서는 루트 서버, .kr TLD 서버, 권한 서버까지 총 3개 DNS 서버에 질의했습니다. 반면 노트북은 평소 설정된 재귀 리졸버에 한 번만 질의하고, 그 리졸버가 뒤의 모든 위임 탐색을 대신 수행합니다.



## Task 2 — DNS Steering and Capture


캡처에서 delegation 응답(패킷 4)은 Answer가 0개이고 Authority에 다음 서버의 NS 레코드 6개가 있었지만, 최종 answer 응답(패킷 8)은 Answer에 www.korea.ac.kr → 163.152.6.10 A 레코드가 직접 들어 있었습니다.

제3자 CDN은 최종 CNAME 호스트명이 Akamai, CloudFront, Fastly 같은 알려진 외부 CDN 접미사에 속하면 yes로 판정했습니다. 최종 이름이 원래 사이트 zone 안에 남으면 no, 그 외 외부 zone은 uncertain으로 표시했습니다. 이 규칙은 www.netflix.com이 netflix.com 내부에서 끝나므로 외부 CDN은 아니라고 올바르게 분류하지만, Netflix가 자체 CDN을 운영한다는 사실은 CNAME zone 비교만으로 식별하지 못합니다. 또한 CNAME이 없는 anycast CDN도 놓칠 수 있습니다.

시스템 리졸버, Google(8.8.8.8), Quad9(9.9.9.9)를 비교했을 때, 제 규칙으로 CDN-hosted로 분류된 7개 사이트 중 7개가 서로 다른 resolver에서 다른 IPv4 주소 집합을 반환했습니다. 이는 DNS 응답이 resolver 위치나 정책에 따라 달라질 수 있음을 보여 주므로 claim (b)를 뒷받침합니다. 다만 실제 서버가 물리적으로 가장 가까운 위치에 있다는 것을 직접 측정한 것은 아닙니다.

+Wireshark/tshark 4.6.8 환경에서 dns.flags.response 필드는 0/1이 아닌 False/True로 출력됩니다.
따라서 실제 DNS query/response가 포함된 pcapng인데도 test_tasks.py가 0 queries, 0 responses로 판정되었습니다.
제 캡처에서는 패킷 3→4가 delegation이고, 7→8이 최종 A 응답입니다.

<img width="1271" height="260" alt="image" src="https://github.com/user-attachments/assets/ce5f71e2-deda-4fcb-a9c2-be5079ea66c4" />



## Task 3 — TTL Cache


정확성 문제: baseline은 authoritative TTL을 무시하고 모든 레코드를 60초 동안 보관합니다. 따라서 TTL이 60초보다 짧은 레코드는 만료된 뒤에도 반환되어 stale answer가 발생합니다.
성능 문제: TTL이 60초보다 긴 레코드도 60초 후 무조건 버리므로, 아직 유효한 데이터를 불필요하게 upstream에 다시 질의합니다.
두 문제의 공통 원인은 레코드별 TTL을 사용하지 않고 고정 60초만 사용하는 것입니다.

올바른 캐시의 floor는 275회 upstream 질의입니다. 각 이름의 첫 질의와 TTL이 만료된 뒤의 첫 질의는 새롭고 유효한 값을 얻기 위해 upstream에 반드시 물어봐야 합니다. 한 응답은 받은 시점부터 해당 TTL 동안만 유효하므로, 만료된 값을 재사용하지 않는 이상 275회보다 더 적은 upstream 질의는 불가능합니다.

baseline이 가장 나쁘게 처리하는 레코드는 www.microsoft.com입니다. 이 이름은 workload에서 가장 자주 선택되고 TTL이 20초로 가장 짧습니다. 그러나 baseline은 60초 동안 저장하므로, 각 저장 구간에서 TTL 만료 후 약 40초 동안 stale 값을 반환할 수 있습니다.

