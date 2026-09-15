# Week 3 Observation



## Task 1 — Iterative DNS Resolver



루트 DNS 서버는 모든 도메인의 최종 IP 주소를 보관하지 않는다. 루트는 `.kr` 같은 TLD를 담당하는 서버로 위임(delegation)하고, TLD 서버는 다시 `korea.ac.kr`의 권한 서버를 알려 준다. 따라서 `www.korea.ac.kr`의 A 레코드를 얻기 위해 루트 → `.kr` TLD → `korea.ac.kr` 권한 서버 순으로 질의했다.



위임 응답에 glue A 레코드가 있으면 그 IP를 바로 다음 질의 대상으로 사용했다. glue가 없다면 NS 호스트명 자체를 루트부터 반복적으로 해석하여 IP를 구한 뒤 원래 위임 탐색을 계속하도록 구현했다. 이번 `www.korea.ac.kr` 실행에서는 필요한 glue가 제공되어, glue 누락 때문에 발생한 추가 조회는 0회였다.



내 노트북은 평소 설정된 재귀 리졸버에 한 번만 질의하지만, 내 resolver는 `www.korea.ac.kr`에 대해 3개 DNS 서버를 직접 질의했다. 검증 결과는 5/5였으며, `dig` 결과와 일치했다.



## Task 2 — DNS Steering and Capture



캡처에서 delegation 응답과 최종 answer 응답은 같은 DNS 패킷 형식이지만 채워지는 섹션이 달랐다. 패킷 3의 질의와 패킷 4의 응답은 Transaction ID `0x8034`로 연결된다. 패킷 4는 Answer가 0개이고 Authority에 NS 레코드가 6개인 delegation 응답이었다. 패킷 7의 질의와 패킷 8의 응답은 Transaction ID `0x1473`으로 연결되며, 패킷 8은 Answer에 `www.korea.ac.kr → 163.152.6.10` A 레코드가 있는 최종 응답이었다.



가장 큰 DNS 응답은 패킷 4이며 크기는 394 bytes였다. `.kr` 위임 과정에서 Authority 섹션의 NS 레코드 6개와 Additional 섹션의 glue A 레코드가 함께 포함되어 크기가 커졌다.



제3자 CDN 판별 규칙은 최종 CNAME 호스트명이 알려진 외부 CDN 접미사(Akamai, CloudFront, Fastly 등)에 속하면 `yes`로 표시하는 방식이다. 최종 이름이 원래 사이트 zone 안에 남으면 `no`, 외부 zone이지만 알려진 CDN 접미사가 아니면 `uncertain`으로 표시했다. 이 규칙은 `www.netflix.com`처럼 최종 이름이 `netflix.com` 내부에 남지만 Netflix 자체 CDN을 사용하는 경우를 놓친다. 또한 CNAME이 없는 anycast CDN도 식별하지 못한다.



시스템 리졸버, Google(8.8.8.8), Quad9(9.9.9.9)를 비교한 결과, 이 규칙으로 CDN-hosted로 분류된 7개 사이트 중 7개가 서로 다른 resolver에 대해 다른 비어 있지 않은 IPv4 주소 집합을 반환했다. 이는 DNS 응답이 resolver 위치 또는 정책에 따라 달라질 수 있음을 뒷받침하지만, 반환된 복제본이 실제로 사용자에게 가장 가까운 서버임을 직접 증명하지는 않는다.



## Task 3 — TTL Cache



BaselineCache의 첫 번째 문제는 정확성이다. authoritative TTL을 무시하고 모든 항목을 고정 60초 동안 보관하기 때문에 TTL이 60초보다 짧은 레코드를 만료 뒤에도 반환한다. 그 결과 baseline은 stale answer를 266개 반환했다.



두 번째 문제는 성능이다. TTL이 60초보다 긴 레코드도 60초가 지나면 버리므로, 아직 유효한 데이터를 불필요하게 upstream에 다시 질의한다. 두 문제의 공통 원인은 authoritative TTL을 사용하지 않는 것이다.



YourCache는 이름별로 `(address, expires\_at)`을 저장하고 `now < expires\_at`일 때만 캐시 값을 반환한다. 따라서 stale answer는 0개가 되었고, upstream 질의는 baseline의 325회에서 275회로 줄었다.



이 워크로드에서 정확한 캐시가 만들 수 있는 upstream 질의의 floor는 275회이다. 각 이름의 첫 질의와 TTL 만료 뒤의 첫 질의는 유효한 응답을 얻기 위해 반드시 upstream에 질의해야 한다. 한 upstream 응답은 그 응답을 받은 시점부터 해당 TTL 동안만 사용할 수 있으므로, 만료된 레코드를 재사용해서 275회보다 더 낮추는 것은 정확성 조건을 위반한다.



Baseline이 가장 나쁘게 처리하는 fixture 레코드는 `www.microsoft.com`이다. 이 이름은 요청 비중이 가장 높고 TTL이 20초로 가장 짧다. Baseline은 이를 60초 동안 보관하므로, 각 저장 구간에서 TTL 만료 후 약 40초 동안 stale 값을 반환할 수 있다.

