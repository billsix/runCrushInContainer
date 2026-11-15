# Rewrite the two-model text to the five-port autodiscovery design

**Status:** proposed — in the 2026-11-15 audit batch
**Priority:** 3
**Difficulty:** 2
**Created:** 2026-11-15 (William Emerison Six <billsix@gmail.com>)
**Source:** tasks/review/2026/11/15/repo-review.md §1.1, §1.6 F7

## BLUF

The code serves five models on fixed ports 8080–8084 and the crushrc autodiscovers them, but many docs still describe two models on 8080/8081. Done means every doc matches the code, and the port coupling `CLAUDE.md` names holds.

## Context

- §1.1 lists each site (`CLAUDE.md:11,29,75`; `README.md:154,168,173,185,290-294,335-351`; `architecture.md:15-18,122-128`; `FORKING.md:8,33`; `new-hardware-bringup.md:20,37`; `crush-capabilities.md:175-177`).
- §1.6: `vendor.sh:7,15,65` and `README.md:379-388` ("BOTH models", ~31 GB); "8 slash commands" (12).

## Plan

1. Rewrite each site; tunnel lines forward 8080–8084.
2. Leave `gemma-4-alongside-glimmer.md` as a decision record.
3. grep `8081` / `both` to confirm.
