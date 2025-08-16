# App Plan
Please mark the finished tasks as per examples.

## What the app needs to do:

This is a dropshipper app which main idea is to scrap through the idealo.de in the search of discounted products. 
The app should should compare them against similar found products on Ebay and make a decision if it is profitable to resell it on local marketplaces (ebaykleinanzeigen.de, marktpaats.nl)
It should send Telegram notification about profitable products and have an interactive dashboard as a webapp.

## Hosting
**Development and testing: local Windows 11 machine
**From Milestone 1 completion: local Ubuntu server

## Techstack:

- **Python**: The core programming language for all custom application logic.
- **SeleniumBase**: The engine used for web scraping to automatically read data from websites.
- **PostgreSQL**: The central database used to store all product and market data.
- **Django**: The web framework for building the administrative dashboard and API.
- **Telegram-Bot**: The library used to send automated alerts to the team's Telegram channel.
- **Docker**: The technology used to package each component of the system into a standardized container.
- **Kubernetes**: The orchestration system that manages, runs, and connects all the Docker containers.
- **Grafana**: (Optional) A monitoring tool for creating visual dashboards of system performance and business metrics.

## MILESTONE 1. Version 0.5: Semiautomation

- [DONE] Scraping idealo.de for products and their prices
- [DONE] Basic dealboard as a webapp
- [DONE] Basic database to get the scraped the data

- [WIP] Ebay scraper
    - connect to db when done and tested
- [WIP] Telegram notifications
    - basic version exists, but need to reiterate on the format of messages.
- [] Feed Gemini with htmls and refactor scraper unit tests

- [] Integrate n8n (not sure how and for which part, yet but 100% need)
- [] Add Gemini 2.5 Flash API to compare the product names 
    from idealo scraper vs ebay scraper, to make a decision if it is the same product.
- [] Wrap all with Kubernetes.
    - [] cronjobs for idealo scraper (schedule every N hours to run), as main entry point.
- [] Add authorization to dealboard for admins (it will contain more specific actions)
- [] Add sorting / filtering to the dealboard
- [] Add another page with all products and all related/scraped data


## MILESTONE 2. Version 1.0: Full Automation

- [] Scrapers for local marketplaces, so that profitable products are posted there automatically
    - [] marktpaats.nl
    - [] ebaykleinanzeigen.de
- [] AI writes human-styled product description for each local market place offer before posting
- [] Create posting for selected marketplace directly from Telegram

## Future:


## Notes:
[Any specific requirements or constraints]