# Public Data Sources for a US Real Estate Investor Research Site

**Purpose.** This is a working reference for scoping a personal research website that surfaces city-level real estate investment data. This is for **personal use only** — not a commercial product — so sources that restrict commercial redistribution (Zillow, Redfin, Apartment List, HUD USPS Vacancy, GreatSchools, Walk Score free tier, etc.) are all usable. It is focused on **public, free, government, and open-data sources** with APIs or bulk downloads — not scraped sources or paid providers (except where a paid provider has a usable free tier).

**How to read this document.**
- Sources are grouped by the investor-facing question category they answer.
- Many sources answer multiple categories — cross-references are noted.
- Each entry captures: URL, coverage, cadence, access method, license/terms notes, and gotchas.
- A final **"Quick-start Recommended Stack"** section prioritizes what to wire up first.
- A **"Terms-of-Use Pitfalls"** section calls out sources that look free but restrict commercial redistribution — read this before shipping anything publicly.

Today's date: 2026-04-15. Release dates and data vintages reflect what is current as of the research window.

---

## 1. Population Growth & Migration

These answer: "Is this city growing? Where are people coming from and going?"

### Census Bureau — Population Estimates Program (PEP)
- **URL:** https://www.census.gov/programs-surveys/popest.html | API: https://www.census.gov/data/developers/data-sets/popest-popproj/popest.html
- **What:** Annual total population, components of change (births, deaths, net domestic migration, net international migration), by year since last decennial.
- **Coverage:** Nation, state, county, CBSA (metro/micropolitan), city/town (incorporated places), Puerto Rico municipios.
- **Cadence:** Annual. Vintage 2025 national/state totals released Jan 2026; full county & metro detail scheduled for June 2026. Components of change are available for 2020–2025.
- **Access:** REST API (Census Data API, free key) + bulk CSV tables.
- **License:** Public domain (US government work). Attribution requested.
- **Limits:** Rate-limited to 500 queries/IP/day without a key; with a key the practical limit is much higher. Up to 50 variables per request.
- **Notes:** This is the canonical source for "how fast is this city/metro growing." PEP blends ACS, IRS migration, Medicare, and birth/death records — it is the single most authoritative growth series below the national level.

### Census Bureau — Decennial Census (2020)
- **URL:** https://www.census.gov/data/developers/data-sets/decennial-census.html
- **What:** Once-a-decade full-count demographic/housing benchmarks (population by age, sex, race, ethnicity; housing tenure/occupancy/vacancy).
- **Coverage:** Down to census block.
- **Cadence:** Every 10 years. Detailed DHC-A and DHC-B files are the richest programmatic 2020 tables.
- **Access:** Census Data API; also bulk FTP.
- **License:** Public domain.
- **Use case:** Benchmarks at the sub-tract level that ACS can't support due to sample size.

### Census Bureau — American Community Survey (ACS)
- **URL:** https://www.census.gov/programs-surveys/acs/data/data-via-api.html
- **What:** Demographics, income, housing costs, commute, educational attainment, tenure, rent, gross rent, rent burden, home values (self-reported), ancestry, language, etc. ~1,775 dataset endpoints across Census APIs.
- **Coverage:** 1-year: geographies ≥65,000 population; 5-year: down to block group / census tract.
- **Cadence:** Annual releases (1-year usually Sept; 5-year usually Dec).
- **Access:** Census Data API (same key/rate limits as PEP). Also `data.census.gov` for interactive downloads and `tidycensus` (R) / `cenpy`, `census` (Python) wrappers.
- **License:** Public domain.
- **Best for:** Sub-county demographic/housing context, rent burden, commute, education — everything an investor wants about who lives there.

### Census Bureau — ACS Migration Flows
- **URL:** https://www.census.gov/data/developers/data-sets/acs-migration-flows.html
- **What:** County-to-county, MCD-to-MCD, and metro-to-metro inflow/outflow/net move counts.
- **Coverage:** County, minor civil division, metro. Latest 5-year file runs 2016–2020 (no published updates beyond that as of early 2026 — a **stale point**).
- **Cadence:** Nominally every few years.
- **Access:** Census Data API.
- **License:** Public domain.
- **Limits:** Lag is significant; flows are 1-year move probabilities averaged over 5 years.

### IRS SOI Migration Data
- **URL:** https://www.irs.gov/statistics/soi-tax-stats-migration-data
- **What:** County-to-county and state-to-state flows of tax returns, exemptions, and aggregate AGI. The gold standard for domestic migration dollars.
- **Coverage:** State and county.
- **Cadence:** Annual. Most recent: calendar years 2022–2023 available as of 2026.
- **Access:** CSV / XLSX bulk downloads (no API).
- **License:** Public domain. Disclosure-suppressed for small counties.
- **Best for:** "Where is the money moving?" — because it reports AGI, you can distinguish a county gaining 1,000 high-earners from one gaining 1,000 low-earners.

### USPS Population Mobility Trends (PMT) / NCOA
- **URL:** https://postalpro.usps.com/pmt
- **What:** Aggregated change-of-address flows; top 9 destination ZIPs per source ZIP.
- **Coverage:** ZIP.
- **Cadence:** Updated periodically via PostalPro.
- **Access:** Downloadable on PostalPro (aggregated tables). **Raw NCOA is licensed only to approved NCOALink service providers** — not a public source.
- **License:** PMT tables are free; raw NCOA requires a commercial license (not appropriate here).
- **Notes:** The free PMT tables are a reasonable consumer-grade signal; if you want "where are people moving from ZIP 10021?" this is the cheapest source.

### HUD Aggregated USPS Vacancy Data
- **URL:** https://www.huduser.gov/portal/datasets/usps.html
- **What:** Quarterly tract/ZIP-level counts of addresses vacant, occupied, no-stat, plus residential/business breakout.
- **Coverage:** Census tract, ZIP.
- **Cadence:** Quarterly.
- **Access:** Controlled-access. HUD restricts this to **governmental entities and registered non-profits** under the HUD–USPS sublicense. **This is NOT appropriate for a commercial site** (see Terms-of-Use Pitfalls).
- **License:** Sublicense only; not redistributable by commercial parties.

---

## 2. Master Plans, Zoning, Development Pipelines, Infrastructure

These answer: "What is being built, what could be built, and what transportation/utilities are coming?"

### Census Building Permits Survey (BPS)
- **URL:** https://www.census.gov/construction/bps/
- **What:** Monthly counts of housing units authorized by building permits, by structure type (1-unit, 2-unit, 3–4-unit, 5+).
- **Coverage:** US, region, state, CBSA (MSA), county, place. Annual detail down to place level.
- **Cadence:** Monthly (revised ~17th workday of the month). Annual permit data for calendar 2025 scheduled May 14, 2026.
- **Access:** Bulk Excel downloads per geography. **No dedicated REST API** — but FRED mirrors aggregate series.
- **License:** Public domain.
- **Best for:** Forward-looking pipeline. More timely than completions data.

### City / County Open Data Portals (Socrata/Tyler, ArcGIS Hub, CKAN)
Large cities publish building permits, certificates of occupancy, construction applications, zoning districts, and land-use projects.
- **NYC Open Data** — https://opendata.cityofnewyork.us/ — DOB permits, PLUTO parcel file, zoning districts. Socrata API with SoQL. Application token raises rate limit to ~1000 req/hr.
- **DataSF** — https://datasf.org/ — SF Planning Department PIM, permits, zoning (Socrata).
- **City of Chicago Data Portal** — https://data.cityofchicago.org/ — Building permits (2006–present), zoning, licenses (Socrata).
- **LA GeoHub / Los Angeles Open Data** — https://geohub.lacity.org/, https://data.lacity.org/ — zoning, permits (Socrata + ArcGIS).
- **Austin Open Data** — https://data.austintexas.gov/ — construction permits, zoning, Imagine Austin plan layers (Socrata).
- **Seattle Open Data** — https://data.seattle.gov/ — SDCI permits, zoning (Socrata).
- **Boston Analyze Boston** — https://data.boston.gov/ — CKAN-based; building permits, zoning BPDA layers.
- **King County / DC / Philadelphia / Denver / Portland** all have similar portals.

**Common pattern:** Most large cities are on **Socrata** (Tyler Technologies) and therefore expose a common REST + SoQL API. Register an app token per city. Some mid-tier cities use **ArcGIS Hub** (Esri) which exposes FeatureServer REST endpoints.

**Rate limits:** Anonymous ~per-hour throttled; with a Socrata app token, ~1000 req/hr.
**Terms:** Most cities publish under open licenses (e.g., NYC: "all data is free to use with attribution"). Always confirm per-dataset.
**Limits:** Coverage is patchy — not every small city has a portal. Schemas vary drastically across cities. No single federated search; you will build per-city connectors.

### Metropolitan Planning Organizations (MPOs) & Regional Councils
- **USDOT MPO directory:** https://www.planning.dot.gov/mpo/
- **ArcGIS hub of boundaries:** https://hepgis-usdot.hub.arcgis.com/
- **What:** Long-range transportation plans (LRTP, typically 20–25 year horizon), Transportation Improvement Programs (TIPs — 4-year funded project list), regional travel demand model outputs.
- **Coverage:** Every urbanized area >50,000. ~400+ MPOs nationally.
- **Cadence:** LRTPs refreshed every 4–5 yrs; TIPs updated 1–2 yr.
- **Access:** Each MPO publishes PDFs + some GIS data; **no unified API**. Examples: SCAG (LA), MTC/ABAG (Bay Area), NYMTC (NYC region), CMAP (Chicago), H-GAC (Houston), NCTCOG (DFW), ARC (Atlanta), PSRC (Seattle), DVRPC (Philly), MWCOG (DC).
- **Limits:** Very heterogeneous. Parsing upcoming-project pipelines at scale is largely a per-MPO scraping job, though the richer agencies (CMAP, SCAG, MTC) publish open-data GIS layers.

### State DOTs
State DOT open-data portals publish STIPs (statewide project funding lists) and often project-level GIS (e.g., Caltrans, FDOT, TxDOT). Pattern similar to MPOs — per-state integration.

### BEA and Census for infrastructure spending context
Not direct project data but useful denominators (state/local government construction expenditures, public capital stock).

### FCC National Broadband Map
- **URL:** https://broadbandmap.fcc.gov/data-download
- **What:** Location-level served/unserved broadband availability by provider and technology.
- **Coverage:** Serviceable location (roughly address-level).
- **Cadence:** Semi-annual (June/Dec) Broadband Data Collection refresh.
- **Access:** Bulk CSV + public REST API (spec: https://www.fcc.gov/sites/default/files/bdc-public-data-api-spec.pdf).
- **License:** Public domain.
- **Use case:** Amenity/infrastructure scoring; "is this neighborhood fiber-served?"

---

## 3. Jobs, Employers, Wages, Unemployment

These answer: "Is this a boom town? Who employs here? Are wages rising?"

### BLS Quarterly Census of Employment and Wages (QCEW)
- **URL:** https://www.bls.gov/cew/
- **What:** Near-census (UI-covered) employment and total wages by industry (NAICS 2- through 6-digit) and geography. Includes establishment size class cuts.
- **Coverage:** US, state, MSA, county. Industry × geography.
- **Cadence:** Quarterly, ~6 month lag.
- **Access:**
  - **Open Data CSVs:** https://www.bls.gov/cew/additional-resources/open-data/ — last 5 years, sliced by industry, area, size. No key required.
  - **BLS Public Data API v2:** https://www.bls.gov/developers/api_signature_v2.htm — requires free `registrationkey`; larger limits than v1 (500 queries/day, 50 series/query, 20 yrs of data per query).
- **License:** Public domain. Commercial use permitted.
- **Best for:** Employer concentration by sector, wage growth by industry.

### BLS Local Area Unemployment Statistics (LAUS)
- **URL:** https://www.bls.gov/lau/
- **What:** Monthly labor force, employment, unemployment, unemployment rate.
- **Coverage:** ~7,500 areas — states, MSAs, counties, larger cities/towns, workforce development areas.
- **Cadence:** Monthly. January 2026 MSA release was scheduled April 16, 2026.
- **Access:** BLS Public Data API v2; also ZIP bulk downloads of recent 14 months.
- **License:** Public domain.
- **Notes:** LAUS is model-based (CPS + CES + UI claims) and revised regularly.

### BLS Occupational Employment and Wage Statistics (OEWS)
- **URL:** https://www.bls.gov/oes/
- **What:** Employment and wages (mean, percentiles) by ~800 occupations.
- **Coverage:** Nation, state, MSA, nonmetropolitan area.
- **Cadence:** Annual (May reference period; released spring following year).
- **Access:** Public Data API, bulk XLS/CSV.
- **License:** Public domain.
- **Use case:** Wage-level signal by occupation — useful for underwriting rent affordability vs. local wage mix.

### BLS Consumer Price Index (CPI)
- **URL:** https://www.bls.gov/cpi/
- **What:** Headline CPI and rent-relevant subindexes: **Rent of primary residence**, **Owners' equivalent rent (OER)**, **Shelter**.
- **Coverage:** Nation, Census region, and ~20+ major metros (CPI-U for metros, semiannual or bimonthly).
- **Cadence:** Monthly nationally; metros vary (some monthly, some bimonthly, some semiannual).
- **Access:** BLS Public Data API v2.
- **License:** Public domain.
- **Notes:** The CPI rent series is a smoothed/lagged benchmark — not a real-time rent index. Pair with Zillow ZORI / Apartment List for leading-edge view.

### Census LEHD LODES (Longitudinal Employer-Household Dynamics — Origin-Destination Employment Statistics)
- **URL:** https://lehd.ces.census.gov/data/
- **What:** Where workers live vs. where they work, at **census block** level. Three files: OD (origin-destination pairs), RAC (residence-area characteristics), WAC (workplace-area characteristics). Cuts by industry, age, earnings, race/ethnicity.
- **Coverage:** Every state except Massachusetts (not a LODES participant historically — worth confirming current status); DC; Puerto Rico; USVI.
- **Cadence:** Annual. 2023 LODES v8 released Dec 18, 2025 (geocoded to 2020 blocks).
- **Access:** Bulk CSV per state + LED Extraction Tool + OnTheMap app.
- **License:** Public domain.
- **Best for:** Commute flows, job density by neighborhood, jobs-housing balance — killer for neighborhood-level investor research.

### Census County Business Patterns (CBP) / ZIP Codes Business Patterns (ZBP)
- **URL:** https://www.census.gov/programs-surveys/cbp.html | API: https://www.census.gov/data/developers/data-sets/cbp-zbp/cbp-api.html
- **What:** Annual establishment counts, employment, payroll by NAICS industry.
- **Coverage:** US, state, county, metro, ZIP (ZBP).
- **Cadence:** Annual, ~2 yr lag. 2023 CBP is latest as of April 2026; 2024 due summer 2026.
- **Access:** Census Data API + CSV downloads (1986–present).
- **License:** Public domain.
- **Notes:** ZBP is the only ZIP-level industry-employment source. Complements QCEW at finer geography.

### BEA Regional Economic Accounts (personal income, GDP)
- **URL:** https://www.bea.gov/data/economic-accounts/regional | API: https://apps.bea.gov/api/signup/
- **What:** Regional GDP by industry, personal income components (wages, transfer receipts, dividends/interest/rent), per-capita personal income, real personal income adjusted for RPP (regional price parities).
- **Coverage:** State, metropolitan area, county.
- **Cadence:** Annual (county/metro GDP ~Dec); personal income quarterly (state) / annual (county).
- **Access:** BEA Data API (free UserID), iTable web interface, bulk downloads.
- **License:** Public domain.
- **Key datasets:** CAINC1 (county personal income summary), CAGDP9 (real GDP by metro/county), MARPI (real personal income by metro).
- **Best for:** Macro context — is the local economy growing in real terms? What sectors drive GDP?

---

## 4. Rents, Vacancy, Rent Levels by Bedroom

These answer: "What rent can I expect? How tight is the market?"

### HUD Fair Market Rents (FMR) / Small Area FMRs (SAFMR)
- **URL:** https://www.huduser.gov/portal/datasets/fmr.html
- **What:** 40th percentile (or 50th where applicable) gross rent by bedroom count (studio–4BR). SAFMRs are at ZIP level for HCV program metros.
- **Coverage:** Every FMR area (metros + nonmetro counties) nationally; SAFMR is ZIP for ~175 metros.
- **Cadence:** Annual (Oct 1 fiscal year start). FY 2026 FMRs published fall 2025; derived from 2023 ACS 1-yr + 2019–2023 ACS 5-yr + local surveys.
- **Access:** HUD API (token required), bulk CSV/XLS, HUD Open Data ArcGIS.
- **License:** Public domain.
- **Best for:** Bedroom-level rent benchmarks — one of the very few free sources with 1BR vs. 2BR vs. 3BR splits.

### HUD CHAS (Consolidated Housing Affordability Strategy)
- **URL:** https://www.huduser.gov/portal/datasets/cp.html | API docs: https://www.huduser.gov/portal/dataset/chas-api.html
- **What:** Custom ACS tabulations for HUD: households by income bracket × housing problems (cost burden, overcrowding, kitchen/plumbing).
- **Coverage:** Nation, state, county, place, tract.
- **Cadence:** Annual 5-year rolling (typically ~18 mo lag).
- **Access:** HUD public API (access token required).
- **License:** Public domain.

### Zillow Research — ZORI (Observed Rent Index) and related
- **URL:** https://www.zillow.com/research/data/
- **What:** ZORI (smoothed, seasonally adjusted market-rate rent index), all homes / SFR / multifamily variants. Plus rent forecast (ZORF) and renter demand index (ZORDI).
- **Coverage:** Nation, metro, city, county, ZIP. (Coverage degrades at ZIP in low-data markets.)
- **Cadence:** Monthly.
- **Access:** CSV downloads from the public research page. Zillow also has an "Econ Data API" for stable programmatic access (recommended over scraping CSV URLs, which change).
- **License:** **This is the commercial red flag.** Zillow Group's Data & API Terms (https://www.zillowgroup.com/developers/terms/) restrict use of Zillow Data to provide a service for other businesses. The Research data is publicly posted but the overarching terms are restrictive; attribution to Zillow is required, and redistribution for commercial purposes is constrained. Treat as "display-only with Zillow attribution, do not resell as data." See Terms-of-Use Pitfalls below.
- **Limits:** No official bedroom-by-bedroom rent series in ZORI. Bedroom-count rent comes from ACS / HUD FMR.

### Apartment List Rent Estimates & Vacancy Index
- **URL:** https://www.apartmentlist.com/research/category/data-rent-estimates + data download page linked from their vacancy index post
- **What:** Rent estimates anchored on ACS recent-mover rents, projected forward using AL platform transaction growth. **Vacancy Index** covers rental vacancy rate trends. **Time on Market** compares listing-to-lease dates.
- **Coverage:** Nation, state, metro, county, city. Back to 2017 for vacancy.
- **Cadence:** Monthly.
- **Access:** CSV downloads from research pages.
- **License:** Not a formal public-domain dataset; historically allowed with attribution, but **their terms should be reviewed before commercial redistribution**. Contact research@apartmentlist.com to confirm.

### Realtor.com Economic Research
- **URL:** https://www.realtor.com/research/data/
- **What:** Monthly and weekly inventory, median list price, days on market, new listings, price-reduced share, hotness index.
- **Coverage:** Nation, metro, ZIP.
- **Cadence:** Weekly and monthly.
- **Access:** CSV downloads.
- **License:** Realtor.com historically permits non-commercial use with attribution; commercial redistribution terms are unclear and should be verified. **Treat similar to Zillow/Redfin — display with attribution, do not resell.**

### Redfin Data Center
- **URL:** https://www.redfin.com/news/data-center/
- **What:** Weekly and monthly housing market data: sale prices, active listings, days on market, sale-to-list ratio, price drops.
- **Coverage:** Nation, state, metro, county, ZIP, neighborhood (where MLS allows). **Some geographies are blocked where local MLS rules prohibit redistribution** — you'll see gaps.
- **Cadence:** Weekly (Wed) and monthly (3rd full Friday).
- **Access:** TSV/CSV bulk downloads linked from the Data Center; also Tableau public viz.
- **License:** Redfin's Data Center is "free to use with attribution" in spirit, but **MLS-level restrictions apply** to some underlying fields. Redfin publishes the data subject to MLS compliance; **commercial redistribution without explicit permission is risky**. Review terms.
- **Notes:** More for-sale oriented than rental, but rental data increasingly included.

### RentCast API (paid, with free tier)
- **URL:** https://www.rentcast.io/api
- **What:** Property-level AVM, rent estimates, comps, listings.
- **Free tier:** 50 API calls/month.
- **License:** Explicitly commercial-friendly (derivative works, storage, display to end-users allowed per their terms) — one of the few paid-with-free-tier sources that's unambiguously OK for commercial products. Still paid above the free tier.

---

## 5. Home Prices, Appreciation, Price-to-Rent

These answer: "Are prices rising? Is this market overvalued?"

### FHFA House Price Index (HPI)
- **URL:** https://www.fhfa.gov/data/hpi | Datasets: https://www.fhfa.gov/data/hpi/datasets
- **What:** Repeat-sales HPI. Multiple variants:
  - **Purchase-Only** (GSE purchase transactions only; the headline)
  - **All-Transactions** (includes refis — more geographies but noisier)
  - **Expanded-Data** (adds FHA + county recorder; now covers 410 metros starting 2026Q1, up from 50)
- **Coverage:** Nation, census division, state, metro, county, ZIP (annual), **census tract (annual)**.
- **Cadence:** Monthly (national/division), quarterly (state/metro/etc.).
- **Access:** CSV/XLS downloads (no formal API). **FRED mirrors the national and many metro series**, which makes programmatic access trivial.
- **License:** Public domain.
- **Best for:** Price appreciation benchmarks. The tract-level annual series is particularly rare among free sources.

### Zillow Research — ZHVI (Home Value Index) and related
- **URL:** https://www.zillow.com/research/data/
- **What:** ZHVI (smoothed typical home value), multiple cuts:
  - All homes / SFR / condo-coop
  - Top-tier (65th–95th pctl) / bottom-tier (5th–35th)
  - **By bedroom count (1BR, 2BR, 3BR, 4BR, 5+BR)**
  - ZHVF forecast (1-, 3-, 12-month ahead)
- **Coverage:** Nation, state, metro, county, city, ZIP, neighborhood.
- **Cadence:** Monthly (16th of month).
- **Access:** CSV downloads + Zillow Econ Data API.
- **License:** Same commercial-use caveats as ZORI (above). Attribution required; redistribution as a data product restricted.
- **Notes:** Much deeper geographic and segmentation coverage than FHFA. The bedroom cuts and neighborhood-level series are unique.

### Redfin Data Center
(See §4 above — same source covers sale prices alongside rent.)

### Home Mortgage Disclosure Act (HMDA) data — CFPB / FFIEC
- **URL:** https://ffiec.cfpb.gov/data-browser/ | Historic: https://www.consumerfinance.gov/data-research/hmda/historic-data/
- **What:** Loan Application Register — loan amount, property value (binned), action type, rate spread, applicant demographics, property type, census tract. 2024 LAR is the latest as of April 2026.
- **Coverage:** Census tract.
- **Cadence:** Annual (~1 yr lag).
- **Access:** HMDA Platform Data Browser with API endpoints, bulk downloads, modified LAR per institution, combined file.
- **License:** Public domain (modified LAR has privacy redactions).
- **Use case:** Investor activity (non-owner-occupied share), lending volume by tract, denial rates by tract — useful gentrification/hot-market signal.

### BEA + FRED price deflators
For real (inflation-adjusted) price-trend normalization, pull BEA regional price parities and FRED CPI series.

### Price-to-Rent
Typically constructed as (ZHVI / (12 × ZORI)) or (FHFA HPI level proxy / ACS median gross rent × 12). No free source publishes a ready-made P/R — compute it yourself.

---

## 6. Neighborhood Quality Signals — Crime, Schools, Walkability, Amenities

These answer: "Is this a good neighborhood? Is it improving?"

### FBI Crime Data Explorer (UCR + NIBRS)
- **URL:** https://cde.ucr.cjis.gov/ | API: https://api.usa.gov/crime/fbi/sapi/
- **What:** Summary UCR offense counts; **NIBRS** incident-level data with offense type, location type, victim/offender demographics. National transition to NIBRS-only as of 2021 — pre-2021 coverage is heterogeneous.
- **Coverage:** Agency, county, state, national. **Not at block or tract** — geography is the reporting agency's jurisdiction.
- **Cadence:** Annual full release; partial quarterly updates.
- **Access:** REST API (free key via api.data.gov/signup/), bulk ZIP downloads of NIBRS master files.
- **License:** Public domain.
- **Limits:** Agency participation varies; some large jurisdictions had reporting gaps in 2021–2022 during NIBRS switch. Pair with city open-data portals (NYPD, LAPD, CPD, etc.) for block-level incidents.
- **Best for:** National baseline + comparability. Augment with local open-data incident feeds for intra-city detail.

### Local Crime Incident Feeds (City Open Data)
- NYC: NYPD Complaint Data (NYC Open Data) — block-level.
- Chicago: Crimes dataset (data.cityofchicago.org).
- LA: LAPD Crime Data (data.lacity.org).
- SF: SFPD Incident Reports (datasf).
- Most large cities publish similar.
- **Pattern:** Socrata APIs; incident lat/lon; refreshed daily to monthly; 2-week reporting lag typical.

### GreatSchools — NearbySchools API
- **URL:** https://www.greatschools.org/api
- **What:** School ratings (1–10), test scores, reviews, assigned school lookups.
- **Coverage:** National, K–12 public + many private.
- **Cadence:** Annual rating refresh.
- **Access:** **Paid API**. Base tier includes 15,000 calls; pay-as-you-go beyond that up to 300k; 14-day free trial. GreatSchools Ratings and assigned-school data require the **Enterprise Data License**.
- **License:** Commercial-use-friendly under their standard API license; attribution required. SaaS/multi-platform use requires Enterprise tier.
- **Notes:** GreatSchools is the de facto industry standard for Zillow/Redfin-style school overlays. Budget for this as a paid line item.

### NCES — Common Core of Data / EDGE
- **URL:** https://nces.ed.gov/programs/edge/ | Open data: https://data-nces.opendata.arcgis.com/
- **What:**
  - **CCD:** Enrollment, demographics, student/teacher ratio, Title I status, free-lunch share for every public school/LEA.
  - **EDGE:** School point locations, school district boundaries, relationship files crosswalking districts to counties/tracts/ZCTAs/CBSAs.
  - **ACS-ED Tabulations:** Demographic/economic profiles of school-age population by district.
- **Coverage:** Every public K–12 school and district in the US.
- **Cadence:** Annual.
- **Access:** ArcGIS REST (EDGE), bulk CSV/XLS, some API endpoints.
- **License:** Public domain.
- **Best for:** Free, authoritative, commercially redistributable alternative to GreatSchools — but ratings are not included. You would construct your own school-quality composite.

### Walk Score API
- **URL:** https://www.walkscore.com/professional/api.php
- **What:** Walk Score, Transit Score, Bike Score for any lat/lon.
- **Free tier:** 5,000 calls/day **for free consumer-facing applications only** — commercial real-estate use typically requires a paid tier. Enterprise quote required.
- **License:** Attribution/linkback required; commercial use requires paid license.

### EPA National Walkability Index (free alternative to Walk Score)
- **URL:** https://www.epa.gov/smartgrowth/smart-location-mapping
- **What:** 1–20 walkability score based on intersection density, proximity to transit, employment/household mix, employment mix.
- **Coverage:** Every Census block group nationally.
- **Cadence:** Periodic (previous major release Jun 2021; v3.0 methodology). Not as current as Walk Score but free.
- **Access:** ArcGIS REST (geodata.epa.gov), bulk shapefile/geodatabase, CSV.
- **License:** Public domain.
- **Best for:** A free, commercially redistributable walkability proxy. Pair with OSM-derived features if you need freshness.

### EPA Smart Location Database (SLD)
- **URL:** https://www.epa.gov/smartgrowth/smart-location-mapping
- **What:** ~90+ block-group attributes on density, diversity, design, destination accessibility, transit accessibility. Underlies the National Walkability Index.
- **Coverage:** Block group, national.
- **Access:** ArcGIS REST, bulk download.
- **License:** Public domain.

### OpenStreetMap / Overpass
- **URL:** https://overpass-api.de/ | Bulk: https://www.geofabrik.de/
- **What:** POI amenities — restaurants, cafes, grocery, parks, transit stops, bike lanes, sidewalks, hospitals, schools — via the `amenity`, `shop`, `leisure`, `highway`, `public_transport` tags.
- **Coverage:** Global, with varying freshness/completeness in the US (typically excellent in major metros).
- **Cadence:** Continuously updated.
- **Access:** Overpass API (rate-limited public instances; self-host for heavy use); Geofabrik regional extracts.
- **License:** **ODbL** — share-alike, attribution required. ODbL applies to **derivative databases**; visual tiles/products can be released under other licenses. This is fine for a web product as long as attribution appears and you respect the share-alike obligation for any derivative **database** you publish.
- **Best for:** Amenity density scoring, 15-minute-city walkability proxies, transit proximity.

### HUD Aggregated USPS Vacancy
Gentrification/abandonment signal — but restricted to gov/nonprofit use (see §1).

### Opportunity Atlas / Opportunity Insights
- **URL:** https://www.opportunityatlas.org/ | Data: https://opportunityinsights.org/data/
- **What:** Tract-level estimates of adult outcomes (income rank at 35, incarceration, teen birth, college) by childhood tract, parent income bracket, race/ethnicity, sex. Plus separate datasets on social capital, college mobility.
- **Coverage:** Census tract, national.
- **Cadence:** Static cohort data (children born 1978–1983 primarily). Augmented with newer releases periodically.
- **Access:** CSV bulk download.
- **License:** Open for research/public use with citation. Commercial use policy should be confirmed with Opportunity Insights for a commercial product.
- **Best for:** Long-run neighborhood-quality signal; very different from current-moment indicators.

### CDC PLACES / 500 Cities
- **URL:** https://www.cdc.gov/places/
- **What:** Census tract-level health outcomes (obesity, diabetes, mental distress, uninsured rate).
- **Coverage:** Tract, national.
- **Access:** Socrata API on data.cdc.gov, CSV.
- **License:** Public domain.

### ATTOM / CoreLogic / Black Knight (paid — flag)
- **ATTOM Developer Platform** — https://api.developer.attomdata.com/ — free trial key with ~10K records, no NDA; full API is paid. Best prototyping path among the big three.
- **CoreLogic** — enterprise only; NDA required for sample data.
- **Black Knight (now ICE)** — enterprise only.
- **Role:** Authoritative parcel/assessor/deeds coverage. If you need owner-of-record, last-sale, AVMs, lien data at scale, this is where you end up. Not free. Regrid, Estated, DataTree are alternatives with friendlier pricing tiers.

---

## 7. General Economic / Demographic Context

### FRED — Federal Reserve Economic Data (St. Louis Fed)
- **URL:** https://fred.stlouisfed.org/ | API: https://fred.stlouisfed.org/docs/api/fred/
- **What:** Aggregator of ~800,000 economic time series from BLS, BEA, Census, FHFA, Fed, IMF, OECD, World Bank, and **Zillow, Freddie Mac, S&P CoreLogic Case-Shiller, ICE Mortgage Monitor, etc.**
- **Coverage:** Nation, region, state, metro, county (varies by series).
- **Cadence:** Per upstream source.
- **Access:** REST API with free key; XML or JSON; also Excel/CSV downloads; official Python (`fredapi`) and R (`fredr`) clients.
- **License:** **Mixed per series.**
  - "Public Domain: Citation requested" — unrestricted use.
  - "Copyrighted: Citation required" (e.g., Case-Shiller, Zillow series on FRED) — can be used for internal commercial use and in publications/reports with attribution to FRED + original source; but **redistribution of the underlying data in bulk is NOT granted by FRED's terms** — you must satisfy the original provider's terms.
- **Notes:** FRED is the single biggest integration accelerant. For any series available on FRED from a public-domain upstream (BLS, Census, FHFA, BEA), it is almost always faster to pull via FRED than the origin.

### data.census.gov
The Census Bureau's omnibus search/UI. Wraps the Census Data API. Good for ad-hoc human exploration; the API is what you wire up.

### US Chamber of Commerce Small Business Index
- **URL:** https://www.uschamber.com/sbindex/data-explorer
- **What:** Quarterly small-business sentiment, hiring/revenue/investment plans by region, sector, business size.
- **Access:** Web-based data explorer; no formal API.
- **Use case:** Soft-signal overlay.

### Commerce Data Hub
- **URL:** https://data.commerce.gov/
- **What:** Department of Commerce unified catalog — aggregates Census, BEA, NOAA, NIST, ITA, EDA datasets.
- **Access:** Catalog + per-dataset downloads/APIs.
- **Use case:** Discovery layer.

### State Economic Development / Commerce Departments
- **Pattern:** Each state has a "department of commerce" or "economic development" agency publishing annual reports, incentive programs, business recruitment data, and often GIS layers of opportunity zones, enterprise zones, and business parks. Examples: Texas Economic Development, Florida Department of Commerce, California GO-Biz, NYC EDC (city-level but massive), Georgia Department of Economic Development. No unified schema — **per-state integration or narrative scraping.**

### Opportunity Zones (IRS / CDFI Fund)
- **URL:** https://www.cdfifund.gov/opportunity-zones
- **What:** Designated tract list (static from 2018), no expiration through 2026; pending reauthorization.
- **Access:** Bulk CSV / shapefile.
- **Use case:** Tax-advantaged investor overlay.

---

## Aggregators and Accelerators

These are **not** raw data sources; they bundle/wrap the raw ones and reduce your integration count.

| Aggregator | What it bundles | Why it saves work |
|------------|-----------------|-------------------|
| **FRED API** | BLS, BEA, Census, FHFA, Fed, Zillow, Case-Shiller, etc. | One API key, consistent JSON, easy charts. Biggest accelerant. |
| **data.census.gov + Census Data API** | ACS, Decennial, PEP, BPS (limited), CBP, Economic Census | Single registration covers ~1,700+ dataset endpoints. |
| **Socrata (Tyler) API pattern** | Most large US cities' open data | Write one connector, parameterize by city domain + dataset ID. |
| **HUD Open Data ArcGIS** | FMR, LIHTC, HCV, opportunity zones | ArcGIS FeatureServer REST. |
| **Commerce Data Hub** | DoC agency catalogs | Discovery; not a unified API. |
| **`tidycensus` (R) / `cenpy` (Python)** | Census APIs | Handles geography joins, margin of error plumbing. |
| **PolicyMap, Urban Institute Data Catalog** | Curated cross-sources | Browsing/QC only (usually behind license for bulk). |

---

## Terms-of-Use Pitfalls (READ BEFORE SHIPPING)

Because this is a **commercial product**, "publicly downloadable" ≠ "redistributable." Call these out explicitly:

| Source | Risk | Mitigation |
|--------|------|------------|
| **Zillow Research (ZHVI, ZORI, etc.)** | Zillow Group Data & API Terms restrict using Zillow Data to provide a service for other businesses; redistribution as a data product is not permitted. | Display with Zillow attribution. Do not expose raw downloadable CSVs to users. Do not resell. Consider whether your product "provides a service for other businesses" — investor tools arguably do; reach out to Zillow for clarification or commercial agreement. |
| **Redfin Data Center** | Published subject to MLS rules; some geographies omitted; commercial redistribution of the underlying data is not explicitly granted. | Display with Redfin attribution + "Data from Redfin, a national real estate brokerage." Do not re-expose raw feeds. |
| **Realtor.com Research** | Commercial redistribution terms unclear. | Same pattern — display with attribution; confirm in writing before building a paid product on it. |
| **Apartment List** | Open research page but formal license not explicit. | Contact research@apartmentlist.com; attribute clearly. |
| **HUD Aggregated USPS Vacancy** | Sublicense restricts access to govt/nonprofits. | **Do not use in a commercial product.** Use HUD FMR + ACS vacancy instead. |
| **USPS NCOA raw** | Licensed to approved NCOALink service providers only. | Use USPS PMT aggregated tables (free) or ACS/IRS flows. |
| **GreatSchools** | API is paid; Ratings + assigned schools require Enterprise license. | Budget for paid tier; or use NCES CCD and build your own composite. |
| **Walk Score** | Free tier is "for free consumer-facing applications only." | Use EPA Walkability Index + OSM amenities for a free, redistributable alternative. |
| **OpenStreetMap / Overpass** | ODbL share-alike applies to **derivative databases** (not to ordinary visual products). | Attribute "© OpenStreetMap contributors"; if you release a derivative database, it must also be ODbL. Don't abuse the public Overpass endpoint — self-host or use Geofabrik extracts at scale. |
| **FRED-hosted copyrighted series (e.g., Case-Shiller)** | Internal/derived use OK with attribution; bulk redistribution not granted via FRED. | Always verify the series' copyright notice in the FRED series metadata before re-exposing the data. |
| **MLS-derived data generally** | Most MLSs prohibit commercial redistribution of listing-level data. | Avoid listing-level data unless licensed (IDX/VOW agreements). Market aggregates are usually fine. |
| **IRS SOI migration** | Public domain; disclosure suppressions for small counties. | Safe. Cite IRS SOI. |
| **All BLS/Census/BEA/FHFA/HUD FMR/CHAS/NCES/FBI/EPA/FCC** | Public domain US government works. | Safe for commercial redistribution. Attribution is courtesy, not legal requirement. |

---

## Quick-Start Recommended Stack

If the goal is to ship a first working version of the site, wire these up in this order. Categories map to the investor questions in the original brief.

### Tier 0 — The "single API key" foundation
1. **FRED API** — gets you national/metro rent CPI, home price indices (FHFA + Case-Shiller), unemployment, personal income, and dozens of Zillow series already republished. One integration, one key, massive coverage.
2. **Census Data API** (one key) — ACS (demographics, housing, rent, commute), PEP (growth), CBP (industry), Decennial benchmarks, migration flows.
3. **BLS Public Data API v2** — QCEW, LAUS, OEWS, CPI rent components.
4. **BEA Data API** — regional GDP, personal income for the macro overlay.

These four APIs alone answer ~70% of the investor-facing questions.

### Tier 1 — Direct downloads to fill gaps
5. **FHFA HPI datasets** (CSVs + tract-level annual) — for ZIP/tract home-price appreciation.
6. **HUD FMR + CHAS** — bedroom-level rent benchmarks + cost burden data.
7. **Census BPS** — monthly building permit pipeline.
8. **LEHD LODES** — commute and jobs-housing balance at block level.
9. **IRS SOI migration** — county-to-county AGI flows.
10. **EPA Walkability Index + Smart Location DB** — free block-group walkability.
11. **Opportunity Atlas** — long-run neighborhood mobility signal.

### Tier 2 — Neighborhood quality overlays
12. **OpenStreetMap Overpass / Geofabrik** — amenity density.
13. **FBI Crime Data API** — national crime baseline.
14. **NCES EDGE + CCD** — school locations, district boundaries, basic stats.
15. **Local crime incident feeds** (NYC, LA, Chicago, SF, etc., via Socrata) — only for the top-N flagship cities you launch with.

### Tier 3 — Private market signals (with attribution and caution)
16. **Zillow Research ZHVI + ZORI** — display-only, Zillow-attributed tiles/charts; do not expose raw CSVs or resell. Revisit commercial terms before scaling.
17. **Apartment List rent + vacancy** — complementary rent view; attribute.
18. **Realtor.com inventory / days on market** — complementary for-sale market tempo; attribute.
19. **Redfin Data Center** — weekly sale-price tempo; attribute.

### Tier 4 — Paid, add when monetization justifies
20. **GreatSchools Enterprise Data License** — for real school ratings + assigned schools.
21. **ATTOM** (or Regrid / Estated) — parcel, assessor, deeds, AVMs.
22. **Walk Score Enterprise** — if you must have the branded score (EPA index is a good free substitute).

### Per-city additions (ship incrementally per launch city)
- The city's open-data portal (Socrata/ArcGIS) for building permits, zoning GIS, code-enforcement, construction permits.
- The city's local MPO for long-range transportation plans and TIP project lists.
- The state DOT for the STIP.
- The city's planning-department master plan PDFs (require light structured extraction).

### "What's the one best source for each investor question?" cheat sheet

| Question | Best starting source |
|----------|----------------------|
| Population/growth | Census PEP (via API or FRED) |
| Migration flows (where from/to) | IRS SOI migration |
| Building permits / pipeline | Census BPS |
| Zoning / master plans | City open-data portal + MPO |
| Job growth | BLS QCEW |
| Employer concentration | BLS QCEW + LEHD LODES |
| Wage levels | BLS OEWS |
| Unemployment | BLS LAUS (or FRED) |
| Rent growth (leading) | Zillow ZORI (display-only) + Apartment List |
| Rent levels by bedroom | HUD FMR / SAFMR |
| Vacancy | ACS + Apartment List Vacancy Index |
| Home prices | FHFA HPI (free redistributable) + ZHVI (display) |
| Appreciation | FHFA HPI tract/ZIP annual |
| Price-to-rent | Computed: ZHVI / (12 × ZORI) |
| Crime baseline | FBI Crime Data Explorer API |
| Crime detail | City open-data incident feeds |
| Schools | NCES CCD (free) + GreatSchools (paid, better) |
| Walkability | EPA Walkability Index (free) or Walk Score (paid) |
| Amenities | OpenStreetMap / Overpass |
| Gentrification indicators | HMDA + ACS 5-yr trends + HUD USPS vacancy (if permitted) + Opportunity Atlas |
| Macro economic context | BEA regional accounts + BLS + FRED |

---

## Appendix — Source URLs Index

**Federal statistical agencies**
- Census developers portal: https://www.census.gov/developers/
- Census Data API key signup: https://api.census.gov/data/key_signup.html
- ACS API: https://www.census.gov/programs-surveys/acs/data/data-via-api.html
- ACS Migration Flows: https://www.census.gov/data/developers/data-sets/acs-migration-flows.html
- Decennial Census APIs: https://www.census.gov/data/developers/data-sets/decennial-census.html
- PEP API: https://www.census.gov/data/developers/data-sets/popest-popproj/popest.html
- CBP/ZBP API: https://www.census.gov/data/developers/data-sets/cbp-zbp.html
- BPS: https://www.census.gov/construction/bps/
- LEHD LODES: https://lehd.ces.census.gov/data/
- BLS developers: https://www.bls.gov/developers/
- BLS API v2 signatures: https://www.bls.gov/developers/api_signature_v2.htm
- QCEW open data: https://www.bls.gov/cew/additional-resources/open-data/
- LAUS: https://www.bls.gov/lau/
- OEWS: https://www.bls.gov/oes/
- CPI: https://www.bls.gov/cpi/
- BEA API signup: https://apps.bea.gov/api/signup/
- BEA regional accounts: https://www.bea.gov/data/economic-accounts/regional

**HUD / FHFA / CFPB / IRS**
- HUD FMR: https://www.huduser.gov/portal/datasets/fmr.html
- HUD CHAS: https://www.huduser.gov/portal/datasets/cp.html
- HUD CHAS API: https://www.huduser.gov/portal/dataset/chas-api.html
- HUD USPS Vacancy (restricted): https://www.huduser.gov/portal/datasets/usps.html
- HUD Open Data ArcGIS: https://hudgis-hud.opendata.arcgis.com/
- FHFA HPI: https://www.fhfa.gov/data/hpi
- FHFA HPI datasets: https://www.fhfa.gov/data/hpi/datasets
- CFPB HMDA Browser: https://ffiec.cfpb.gov/data-browser/
- IRS SOI migration: https://www.irs.gov/statistics/soi-tax-stats-migration-data

**FRED**
- https://fred.stlouisfed.org/docs/api/fred/
- Terms: https://fred.stlouisfed.org/docs/api/terms_of_use.html
- Key: https://fred.stlouisfed.org/docs/api/api_key.html

**Private research data (redistribution-restricted)**
- Zillow Research: https://www.zillow.com/research/data/
- Zillow Developer Terms: https://www.zillowgroup.com/developers/terms/
- Redfin Data Center: https://www.redfin.com/news/data-center/
- Realtor.com Research: https://www.realtor.com/research/data/
- Apartment List research: https://www.apartmentlist.com/research

**Neighborhood quality**
- FBI Crime Data Explorer: https://cde.ucr.cjis.gov/
- FBI Crime API signup: https://api.data.gov/signup/
- GreatSchools API: https://www.greatschools.org/api
- NCES EDGE: https://nces.ed.gov/programs/edge/
- NCES EDGE Open Data: https://data-nces.opendata.arcgis.com/
- Walk Score API: https://www.walkscore.com/professional/api.php
- EPA Smart Location Mapping: https://www.epa.gov/smartgrowth/smart-location-mapping
- EPA Walkability Index dataset: https://catalog.data.gov/dataset/walkability-index8
- OpenStreetMap Overpass: https://overpass-api.de/
- Geofabrik extracts: https://www.geofabrik.de/
- Opportunity Atlas: https://www.opportunityatlas.org/
- Opportunity Insights data: https://opportunityinsights.org/data/
- CDC PLACES: https://www.cdc.gov/places/

**City open data portals**
- NYC: https://opendata.cityofnewyork.us/
- DataSF: https://datasf.org/
- Chicago: https://data.cityofchicago.org/
- LA: https://data.lacity.org/ and https://geohub.lacity.org/
- Austin: https://data.austintexas.gov/
- Seattle: https://data.seattle.gov/
- Boston: https://data.boston.gov/
- Socrata developer docs: https://dev.socrata.com/

**Infrastructure / broadband**
- FCC National Broadband Map: https://broadbandmap.fcc.gov/
- FCC BDC API spec: https://www.fcc.gov/sites/default/files/bdc-public-data-api-spec.pdf
- USDOT MPO directory: https://www.planning.dot.gov/mpo/

**Paid (noted for completeness)**
- ATTOM Developer Platform: https://api.developer.attomdata.com/
- RentCast: https://www.rentcast.io/api
