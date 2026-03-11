
# Known Issues

## 1) "gosu built with old Go stdlib" CVEs in upstream images
Many official images ship `gosu` compiled with an older Go toolchain. Container scanners may flag this.
Status: Track upstream. Document risk acceptance / mitigation strategy.

Mitigation options:
- Accept & document (short-term)
- Replace gosu / build custom images (mid-term)
- Wait for upstream rebuild (unknown)

## 2) Scanner methodology drift
Different scanners and database updates can change CVE counts over time.
Action: Keep weekly scans + pin images + track deltas.
