# Week 7

## Task 1 — Learning Switch

수신 포트로 프레임을 재전송하면 중복 전송과 네트워크 루프 문제가 발생할 수 있다. 스위치는 알 수 없는 목적지에 Flooding을 수행하지만, 라우터는 경로가 없으면 패킷을 폐기한다.
Aging은 300초가 지난 MAC 항목을 삭제하지만 장치 이동을 즉시 감지하지 못하며, 링크 상태 확인이나 새로운 프레임 수신으로 이를 보완할 수 있다. 검증 7개를 모두 통과했다.

## Task 2 — ARP Observation

ARP 테이블은 삭제 전 7개, 삭제 직후 3개, 통신 후 4개였으며 게이트웨이(172.16.9.1)가 유일한 동적 항목이었다. 외부 서버의 MAC은 ARP가 로컬 링크의 다음 홉 주소만 확인하므로 등록되지 않는다.
ARP Request는 브로드캐스트(ff:ff:ff:ff:ff:ff), Reply는 요청자에게 유니캐스트(08:6a:c5:87:e7:2c)되었다. 최초 1분간 2개가 관찰되어 100대 기준 분당 약 200개로 추정되며, 검증 4개를 모두 통과했다.

## Task 3 — MAC Table Eviction

FIFO 대신 LFU와 주기적 빈도 감소를 적용하고, 사용 빈도가 낮은 신규 MAC의 학습을 거부하는 Admission Control을 구현했다. Wasted Deliveries는 323,380에서 159,114로 50.8% 감소했고 Missed는 0으로 유지되어 Strong 등급을 달성했다.
위조 MAC 주소를 대량 전송하면 테이블이 오염되어 Flooding이 증가하는 MAC Flooding 공격이 발생할 수 있으며, 포트별 MAC 학습 수 제한(Port Security)으로 완화할 수 있다.
