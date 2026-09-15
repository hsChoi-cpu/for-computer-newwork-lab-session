#!/usr/bin/env python3
"""Week 3 · Task 2 — Does DNS actually steer you? Measure it."""

import argparse
import ipaddress
import json
import os
import subprocess


HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CHAINS_PATH = os.path.join(OUT, "chains.json")
REPORT_PATH = os.path.join(OUT, "report.md")

SITES = [
    "www.microsoft.com",
    "www.netflix.com",
    "www.adobe.com",
    "www.cnn.com",
    "www.apple.com",
    "www.korea.ac.kr",
    "www.stanford.edu",
    "www.bbc.co.uk",
    "www.spotify.com",
    "www.github.com",
    "www.wikipedia.org",
    "www.nytimes.com",
]

RESOLVERS = {
    "system": None,
    "google": "8.8.8.8",
    "quad9": "9.9.9.9",
}

# 이 접미사들은 외부 CDN 사업자임을 비교적 명확히 보여 준다.
KNOWN_THIRD_PARTY_CDN_SUFFIXES = (
    "akamai.net",
    "akamaiedge.net",
    "edgekey.net",
    "edgesuite.net",
    "cloudfront.net",
    "fastly.net",
    "fastlylb.net",
    "azureedge.net",
    "cdn77.org",
    "cloudflare.net",
    "hwcdn.net",
)


def dig(name, rtype="A", server=None):
    """dig를 전송 수단으로만 사용해 DNS 레코드를 조회한다."""
    args = ["dig", "+short", name, rtype]

    if server:
        args.insert(1, f"@{server}")

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError("dig 명령을 찾을 수 없습니다.") from exc

    if result.returncode != 0:
        return []

    return [
        line.strip().rstrip(".")
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def is_ipv4(value):
    """value가 IPv4 주소인지 확인한다."""
    try:
        return isinstance(ipaddress.ip_address(value), ipaddress.IPv4Address)
    except ValueError:
        return False


def cname_chain(name, server=None, max_hops=15):
    """
    CNAME을 한 단계씩 직접 따라간다.

    반환값은 [원래 이름, CNAME 대상, ..., 최종 이름] 형태다.
    """
    chain = [name.rstrip(".")]
    current = chain[0].lower()

    for _ in range(max_hops):
        targets = dig(current, "CNAME", server)

        if not targets:
            return chain

        target = targets[0].lower().rstrip(".")

        if target in chain:
            raise RuntimeError(f"CNAME loop detected: {' -> '.join(chain + [target])}")

        chain.append(target)
        current = target

    raise RuntimeError(f"CNAME chain exceeded {max_hops} hops for {name}")


def addresses_for(name, server=None):
    """name의 A 레코드 집합을 반환한다."""
    return sorted({answer for answer in dig(name, "A", server) if is_ipv4(answer)})


def final_zone(name):
    """
    보기 쉬운 최종 zone 표기.

    완전한 Public Suffix List 구현은 아니지만 report의 비교용으로 충분하다.
    """
    labels = name.rstrip(".").lower().split(".")

    if len(labels) < 2:
        return name.rstrip(".")

    # bbc.co.uk처럼 흔한 2단계 국가 코드 TLD를 조금 더 정확히 표시한다.
    if len(labels) >= 3 and labels[-2] in {"co", "ac", "org", "net", "gov"}:
        if len(labels[-1]) == 2:
            return ".".join(labels[-3:])

    return ".".join(labels[-2:])


def third_party_verdict(site, endpoint):
    """
    (third_party?, rule_verdict)을 반환한다.

    yes: 알려진 외부 CDN 접미사
    no: 최종 도메인이 원래 사이트의 zone 안에 있음
    uncertain: 다른 zone이지만 알려진 CDN 접미사는 아님
    """
    endpoint = endpoint.lower().rstrip(".")
    site_zone = final_zone(site)

    for suffix in KNOWN_THIRD_PARTY_CDN_SUFFIXES:
        if endpoint == suffix or endpoint.endswith("." + suffix):
            return "yes", f"known third-party CDN suffix: {suffix}"

    if endpoint == site_zone or endpoint.endswith("." + site_zone):
        return "no", "final hostname remains in the site's own zone"

    return "uncertain", "different final zone, but not a known CDN suffix"


def collect():
    """
    모든 사이트에 대해 resolver별 CNAME chain 및 A address set을 수집한다.

    결과는 out/chains.json에 저장된다.
    """
    results = {
        "sites": {},
        "resolvers": RESOLVERS,
    }

    for site in SITES:
        print(f"Collecting {site} ...")
        site_results = {}

        for resolver_name, resolver_ip in RESOLVERS.items():
            try:
                chain = cname_chain(site, resolver_ip)
                endpoint = chain[-1]
                addresses = addresses_for(endpoint, resolver_ip)

                site_results[resolver_name] = {
                    "resolver_ip": resolver_ip,
                    "chain": chain,
                    "addresses": addresses,
                    "error": None,
                }
            except Exception as exc:
                site_results[resolver_name] = {
                    "resolver_ip": resolver_ip,
                    "chain": [],
                    "addresses": [],
                    "error": repr(exc),
                }

        results["sites"][site] = site_results

    with open(CHAINS_PATH, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)

    print(f"Wrote {CHAINS_PATH}")


def addresses_differ(site_data):
    """두 개 이상의 resolver가 서로 다른 non-empty A record set을 주었는가?"""
    address_sets = set()

    for resolver_data in site_data.values():
        addresses = resolver_data.get("addresses", [])

        if addresses:
            address_sets.add(tuple(addresses))

    return len(address_sets) > 1


def report():
    """chains.json을 읽어 out/report.md를 생성한다."""
    if not os.path.exists(CHAINS_PATH):
        raise FileNotFoundError(
            f"{CHAINS_PATH} does not exist. Run with --collect first."
        )

    with open(CHAINS_PATH, encoding="utf-8") as file:
        data = json.load(file)

    lines = [
        "# DNS Steering Measurement",
        "",
        "## Method",
        "",
        "Each hostname was queried through the system resolver, Google "
        "(8.8.8.8), and Quad9 (9.9.9.9). The script followed CNAME records "
        "one hop at a time and compared the final A-record address sets.",
        "",
        "Third-party rule: a site is marked **yes** only when its final "
        "hostname matches a known external CDN suffix, such as Akamai, "
        "CloudFront, or Fastly. A hostname remaining in the site's own zone "
        "is marked **no**. All other cases are **uncertain**.",
        "",
        "## CNAME chains and CDN classification",
        "",
        "| Site | Chain length | Final zone | Third party? | Rule verdict |",
        "|---|---:|---|---|---|",
    ]

    cdn_sites = []
    steering_sites = 0

    for site in SITES:
        site_data = data["sites"].get(site, {})
        system_data = site_data.get("system", {})
        chain = system_data.get("chain", [])

        # system resolver가 실패했다면 성공한 첫 resolver 결과를 표에 사용한다.
        if not chain:
            for candidate in site_data.values():
                if candidate.get("chain"):
                    chain = candidate["chain"]
                    break

        if not chain:
            lines.append(
                f"| {site} | — | — | — | "
                "all resolver measurements failed; inspect chains.json |"
            )
            continue

        endpoint = chain[-1]
        third_party, verdict = third_party_verdict(site, endpoint)
        chain_length = len(chain) - 1

        if third_party == "yes":
            cdn_sites.append(site)

            if addresses_differ(site_data):
                steering_sites += 1

        lines.append(
            f"| {site} | {chain_length} | {final_zone(endpoint)} | "
            f"{third_party} | {verdict} |"
        )

    lines.extend([
        "",
        "## Steering result",
        "",
        f"**{steering_sites} of {len(cdn_sites)}** CDN-hosted sites "
        "answered with a different non-empty IPv4 address set to a "
        "different resolver.",
        "",
        "Different address sets are evidence that DNS answers may be "
        "steered by resolver location or policy. They do not by themselves "
        "prove that the returned server is geographically closest to the "
        "user.",
        "",
        "## Rule limitation / known mistake",
        "",
        "A rule based only on the final domain zone cannot identify all CDN "
        "deployments. `www.netflix.com` can stay inside `netflix.com` while "
        "being served by Netflix's own CDN, so a same-zone result does not "
        "mean that no CDN is involved. Likewise, anycast CDN deployments may "
        "have no CNAME chain at all. The rule therefore classifies third-party "
        "hosting, not every possible CDN deployment.",
        "",
        "Raw data: `out/chains.json`.",
    ])

    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")

    print(f"Wrote {REPORT_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    os.makedirs(OUT, exist_ok=True)

    if args.collect:
        collect()
    elif args.report:
        report()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
