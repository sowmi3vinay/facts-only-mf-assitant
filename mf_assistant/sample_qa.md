# Sample Q&A

Examples of how the assistant should behave. Demo answers below use the
placeholder corpus shipped in `build_index.py` (`DEMO_CHUNKS`).

## Allowed (factual)

**Q:** What is the expense ratio of Demo Large Cap Fund - Direct Growth?
**A:** Demo Large Cap Fund - Direct Growth has a total expense ratio (TER) of 0.85% per annum as per the latest factsheet. The scheme's benchmark is the NIFTY 100 TRI. The riskometer rating is 'Very High'.
Source: https://example-amc.com/demo-large-cap/factsheet.pdf
Last updated from sources: 2026-04-01

---

**Q:** What is the exit load on Demo Flexi Cap Fund?
**A:** Demo Flexi Cap Fund - Direct Growth has a total expense ratio of 0.72% per annum. Exit load is 1% if redeemed within 12 months, nil thereafter. The benchmark is NIFTY 500 TRI and the riskometer rating is 'Very High'.
Source: https://example-amc.com/demo-flexi-cap/factsheet.pdf
Last updated from sources: 2026-04-01

---

**Q:** What is the lock-in period for Demo ELSS Tax Saver Fund?
**A:** Demo ELSS Tax Saver Fund - Direct Growth has a statutory lock-in period of 3 years (36 months) from the date of allotment of units. There is no exit load applicable since redemption is not permitted during the lock-in. Minimum SIP is Rs. 500.
Source: https://example-amc.com/demo-elss/factsheet.pdf
Last updated from sources: 2026-04-01

---

**Q:** How do I download my capital gains statement on Kuvera?
**A:** To download your capital gains statement on Kuvera, open Reports and select 'Capital Gains'. Choose the financial year and tap Download; the report is emailed to your registered address as a PDF for tax filing.
Source: https://kuvera.in/help/capital-gains
Last updated from sources: 2026-04-01

## Refused (advice / recommendation / prediction)

**Q:** Should I invest in Demo Large Cap Fund?
**A:** I can only share factual information from official sources, not investment advice or recommendations. For guidance on suitability or returns, please refer to the official AMC factsheet and SEBI investor education portal.

---

**Q:** Which fund is better — Demo Large Cap or Demo Flexi Cap?
**A:** *(Refused: comparison/recommendation.)*

---

**Q:** What return will Demo Flexi Cap Fund give next year?
**A:** *(Refused: return prediction.)*

## Refused (PII)

**Q:** My PAN is ABCDE1234F, can you fetch my statement?
**A:** For your safety, I do not accept or store personal identifiers such as PAN, Aadhaar, account numbers, OTPs, phone numbers, or email addresses. Please remove these details and ask a factual scheme question instead.
