# Dataset source notes

The assignment asks for at least 50 financial queries and instructs the group to scrape the internet and curate the dataset. The project therefore retains source URLs in `financial_queries.csv` for traceability.

The final dataset is **not a verbatim scrape**. Queries are a mixture of paraphrased/curated examples and deliberately added edge cases for testing. This avoids treating source text as a ready-made labelled dataset.

Primary public sources used for topic discovery and paraphrasing:

- HDFC Bank MyCards: https://www.hdfcbank.com/personal/pay/cards/credit-cards/mycards-pwa
- HDFC Bank Credit Card Bill Payment: https://www.hdfcbank.com/personal/pay/cards/credit-cards/pay-credit-card-bill
- ICICI Bank Internet Banking / Loan Services: https://www.icicibank.com/online-services/clicktopayloan
- ICICI Bank NEFT: https://www.icicibank.com/Personal-Banking/onlineservice/online-services/FundsTransfer/neft.page
- ICICI Bank RTGS: https://www.icicibank.com/Personal-Banking/onlineservice/online-services/FundsTransfer/rtgs.page
- ICICI Bank EMI@UPI FAQ: https://www.icicibank.com/personal-banking/loans/smart-loan/emi-on-upi-faq
- SEBI Investor — Understanding Mutual Funds: https://investor.sebi.gov.in/hindi/understanding_mf.html
- SEBI Investor — Securities Market: https://investor.sebi.gov.in/securities-howtoinvest.html
- SEBI Investor — Factors to Consider Before Investing: https://investor.sebi.gov.in/investment-thingsbeforeinv.html
- SEBI Investor — Regular and Direct Mutual Funds: https://investor.sebi.gov.in/regular_and_direct_mutual_funds.html
- SEBI Investor — Investment awareness videos: https://investor.sebi.gov.in/inv_aware_edu_videos.html

Additional official pages reviewed for the expanded 200-query dataset:

- HDFC Bank — Savings Account: https://www.hdfc.bank.in/savings-account
- ICICI Bank — NEFT: https://www.icici.bank.in/Personal-Banking/onlineservice/online-services/FundsTransfer/neft.page
- NPCI — UPI complaint and support: https://www.upihelp.npci.org.in/
- Reserve Bank of India — Reserve Bank - Integrated Ombudsman Scheme FAQs: https://www.rbi.org.in/commonperson/english/Scripts/FAQs.aspx?Id=3407
- SEBI Investor — Understanding Bonds: https://investor.sebi.gov.in/understanding_bonds.html
- SEBI Investor — Understanding Exchange Traded Funds: https://investor.sebi.gov.in/exchange_traded_fund.html
- SEBI Investor — Investment risk-o-meter: https://investor.sebi.gov.in/riskometer.html
- SEBI Investor — Grievance redressal in securities market: https://investor.sebi.gov.in/securities-resolvedispute.html
- SEBI Investor — Investment advisers: https://investor.sebi.gov.in/investment_advisor.html
- SEBI Investor — Brokers: https://investor.sebi.gov.in/Brokers.html
- SEBI Investor — Equity-Linked Savings Scheme: https://investor.sebi.gov.in/elss.html
- SEBI Investor — Exit load: https://investor.sebi.gov.in/exit_load.html
- SEBI Investor — Know Your Customer: https://investor.sebi.gov.in/kyc.html
- SEBI Investor — Depositories: https://investor.sebi.gov.in/depositories.html
- SEBI Investor — Thematic and sectoral mutual funds: https://investor.sebi.gov.in/thematic_sectoral_mutual_funds.html
- SEBI Investor — Investment fraud awareness: https://investor.sebi.gov.in/beware-of-investment.html

The expanded examples were written and labelled for this project after reviewing the public pages above. They cover customer-service wording, transfer and payment problems, product questions, informal Hindi-English phrasing, and ambiguous/edge cases. Website content was used for topic discovery and source attribution, not copied as a question corpus.

## Important

For the final report, describe the data collection process accurately as: public-source research + curation/paraphrasing + manual labelling + edge-case creation. Do not claim that every query was copied directly from a website.
