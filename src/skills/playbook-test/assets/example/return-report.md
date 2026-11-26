DONE: SHOP-TEST, 3 functions tested on staging, 2 fail
Ask: test the shop on staging before the release
Did: planned the expected results, ran them in a real browser and ran the failures again, with an agent on the medium row
Result: price quote passes; discount code fails (500, 2 of 2 runs); report download fails (4.0 s over a 2 s budget, 2 of 2); report /home/example/test-evidence/shop-stg/report.md; I opened the key frames of both failures
Caveats: payment was not tested: it would charge a real card; one browser at 1280x800 only; no issue was filed
Needs: decide whether to file the 2 bugs in the report
From: bot:Tester (example), chat 8c1d0e22-aaaa-bbbb-cccc-ddddeeeeffff
