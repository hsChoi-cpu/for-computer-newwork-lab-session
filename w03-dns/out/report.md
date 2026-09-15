# DNS Steering Measurement

## Method

Each hostname was queried through the system resolver, Google (8.8.8.8), and Quad9 (9.9.9.9). The script followed CNAME records one hop at a time and compared the final A-record address sets.

Third-party rule: a site is marked **yes** only when its final hostname matches a known external CDN suffix, such as Akamai, CloudFront, or Fastly. A hostname remaining in the site's own zone is marked **no**. All other cases are **uncertain**.

## CNAME chains and CDN classification

| Site | Chain length | Final zone | Third party? | Rule verdict |
|---|---:|---|---|---|
| www.microsoft.com | 2 | akamaiedge.net | yes | known third-party CDN suffix: akamaiedge.net |
| www.netflix.com | 1 | netflix.com | no | final hostname remains in the site's own zone |
| www.adobe.com | 2 | akamai.net | yes | known third-party CDN suffix: akamai.net |
| www.cnn.com | 1 | fastly.net | yes | known third-party CDN suffix: fastly.net |
| www.apple.com | 3 | akamaiedge.net | yes | known third-party CDN suffix: akamaiedge.net |
| www.korea.ac.kr | 0 | korea.ac.kr | no | final hostname remains in the site's own zone |
| www.stanford.edu | 1 | netlifyglobalcdn.com | uncertain | different final zone, but not a known CDN suffix |
| www.bbc.co.uk | 2 | fastly.net | yes | known third-party CDN suffix: fastly.net |
| www.spotify.com | 1 | fastly.net | yes | known third-party CDN suffix: fastly.net |
| www.github.com | 1 | github.com | no | final hostname remains in the site's own zone |
| www.wikipedia.org | 1 | wikimedia.org | uncertain | different final zone, but not a known CDN suffix |
| www.nytimes.com | 3 | fastly.net | yes | known third-party CDN suffix: fastly.net |

## Steering result

**7 of 7** CDN-hosted sites answered with a different non-empty IPv4 address set to a different resolver.

Different address sets are evidence that DNS answers may be steered by resolver location or policy. They do not by themselves prove that the returned server is geographically closest to the user.

## Rule limitation / known mistake

A rule based only on the final domain zone cannot identify all CDN deployments. `www.netflix.com` can stay inside `netflix.com` while being served by Netflix's own CDN, so a same-zone result does not mean that no CDN is involved. Likewise, anycast CDN deployments may have no CNAME chain at all. The rule therefore classifies third-party hosting, not every possible CDN deployment.

Raw data: `out/chains.json`.
