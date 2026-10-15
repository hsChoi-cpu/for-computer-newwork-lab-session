# Week 06 Observation

## Task 1
동일 비용 경로에서는 first hop 이름이 사전순으로 앞선 경로를 선택했다. 
u→w는 직접 비용 5보다 u-x-y-w 비용 3이 작아 next hop이 x였고, u-x 단절 후에는 v를 제외한 w·x·y·z가 모두 v로 우회했다.

## Task 2
국내 경로는 고려대망 이후 외부망으로 넘어갔고, 해외 경로는 Tokyo 약 40 ms에서 Seattle 약 144~202 ms로 RTT가 크게 증가해 태평양 횡단 구간으로 판단했다.
r1-r2 링크 단절 후 재수렴은 1초였으며, cost 10→100 변경 시 링크를 끊지 않고도 경로가 우회 경로로 이동했다.

## Task 3
현재 거리와 SPT parent 정보를 유지해 영향 없는 link down/cost 증가에서는 SPF를 생략하고, link up/cost 감소는 증분 갱신했다.
그 결과 SPF 실행을 1001회에서 242회로 줄여 76%를 회피했고, 모든 이벤트에서 정답을 유지했지만 Python wall time은 1.96초→2.30초로 조금 증가했다.
