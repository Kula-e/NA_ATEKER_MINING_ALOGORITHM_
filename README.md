# TURKSOIL LIMITED website and contract checkout

The page can run without payment configuration, but a real £26 GBP contract-download charge requires the Python server and a Stripe account. There is no simulated-payment path. The server creates a fixed-price Stripe Checkout session, stores only the encrypted `_NA_CRYPTO` package, and checks the Checkout session directly with Stripe before releasing the file. The webhook records signed Stripe events; it is not treated as proof by itself.

The **Encrypted payment request** panel can prepare a local `_NA_CRYPTO` payment-request draft: enter the request details and a 12+ character passphrase, then download the encrypted JSON. Open it again from **Services → Contract** with the same passphrase. This is encryption, not cryptocurrency, a Stripe charge, or payment confirmation; card and bank details are not requested or collected there. Actual Stripe checkout in this app is currently limited to the fixed £26 encrypted service-contract download.

The site opens in the **Customer** interface, which focuses on services and contract information. The WordPress theme requires a signed-in WordPress administrator (`manage_options`) to open **Admin**, using the site's normal WordPress sign-in. The standalone Python server uses an expiring server-issued session; configure `TURKSOIL_ADMIN_PASSWORD` with at least 16 characters before starting it. Set secrets in the hosting environment, never in the page, source control, or chat. Sign-in is rate-limited, and the standalone session cookie is HTTP-only and same-site (and secure when the configured site URL uses HTTPS).

The current dashboard controls are browser-side visualizations, not privileged server operations or private records. Any future admin data or changes must also be authorized by the server on each API request; hiding a page or validating sign-in only in JavaScript is not an authorization boundary.

To configure the standalone Windows preview without entering a password in chat or putting it in the project, open PowerShell in this directory and run `& '.\Configure Turksoil Admin Password.ps1'`. Enter your chosen password twice at the secure prompts; use at least 16 characters. The script saves it in your Windows user environment, restarts the local site, and opens it in your browser. Keep the launcher window open while using the site. This local setting does not change IONOS or WordPress credentials.

## Run locally

On Windows, install Python 3 and double-click **Start Turksoil.bat**. It starts the local app server, opens the unified spaceship-and-services system in your default browser, and keeps the server running until you press Enter in the launcher window. Closing the launcher stops only the server process it started. If the site is already running on the configured port, the launcher reuses it without stopping it. Checkout is disabled by default; local Stripe checkout can be opted into only with a Stripe test key:

```powershell
$env:TURKSOIL_ENABLE_STRIPE = "1"
$env:STRIPE_SECRET_KEY = "sk_test_replace_with_your_test_key"
$env:STRIPE_WEBHOOK_SECRET = "whsec_replace_with_your_test_webhook_secret"
$env:TURKSOIL_ADMIN_PASSWORD = "replace_with_a_unique_password_of_16_chars_or_more"
& '.\Start Turksoil.bat'
```

The launcher rejects live Stripe keys when test checkout is opted in. To verify server startup without opening the browser, run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_turksoil.ps1 -CheckOnly`.

From this directory in PowerShell, set a Stripe **test-mode** secret and start the standard-library-only server:

```powershell
$env:STRIPE_SECRET_KEY = "sk_test_replace_with_your_test_key"
$env:STRIPE_WEBHOOK_SECRET = "whsec_replace_with_your_webhook_secret"
$env:TURKSOIL_ADMIN_PASSWORD = "replace_with_a_unique_password_of_16_chars_or_more"
$env:SITE_BASE_URL = "http://localhost:8000"
python server.py
```

Open `http://localhost:8000`. Configure the Stripe CLI or dashboard webhook endpoint as `http://localhost:8000/api/stripe/webhook` for local testing, and subscribe to `checkout.session.completed`, `checkout.session.async_payment_succeeded`, and `checkout.session.async_payment_failed`. The CLI's forwarding URL can be used to receive local webhook events. Never put Stripe secrets in `index.html`, browser storage, or a checked-in file.

The `_NA_` ship itself is an interactive on-page visual simulation. Mission profiles (Cruise, Survey, Orbit, Transit), simulated throttle, dimension selection, pause/resume, drag-to-rotate, and scroll-to-zoom adjust the display; they are not real spacecraft commands or telemetry.

The **Compute** tab is a hardware-themed visualization and page-rendering control, not a hardware detector or installer. It labels Intel Core as an illustrative CPU role, Intel Iris Xe as Intel integrated graphics, NVIDIA GeForce/RTX as an optional GPU reference, and Microsoft Windows as a software/OS layer (not a chip). The page currently uses Canvas 2D and does not select or connect to a physical GPU. Its 4/8/16/32 GB demand-responsive memory pool is simulated from the selected visual dimension, mission profile, and throttle; it neither allocates memory nor upgrades physical RAM. Adaptive, Balanced, Eco, and Performance modes adjust this page's animation frame-rate and canvas-resolution caps; at high dimensions, the lower-load modes also sample fewer visual nodes/links, with the current sample ratio shown in the panel. The renderer batches link strokes, caches dimension geometry, and reuses simulation-state buffers to reduce drawing overhead and per-frame allocations.

On a mouse/pen device, the **Cursor** control cycles through Prism, Orbit, Spark, and Off. The overlay picks up saturated foreground/background colors from the element under the pointer and draws a brief matching trail and click pulse. It does not intercept clicks, preserves the native text-entry cursor, is omitted on touch-first devices, and suppresses trail/pulse motion when reduced motion is requested.

The left-side **System demand** mini-dashboard shows a speedometer-style overall estimate and CPU, graphics, simulated-memory, and rendering meters. It derives these values from the page's visual dimension, mission profile, throttle, and rendering mode; it models the page's workload, not live readings from the computer's processor, graphics card, or RAM. The compact panel is repositioned and reduced on mobile to stay clear of the page title and payment panel.

In **Services → Pricing**, choose **Global / international project** or a country/territory from the worldwide selector. Each of the 15 services now shows a service-specific compliance and cost checklist for the selected country or, in Global mode, a cross-border checklist. The five researched mining jurisdictions (Kenya, Uganda, Tanzania, Ghana, and South Africa) retain their mining framework, small-scale and industrial licensing routes, regulator sources, and fee status; this researched guide applies to Gemstone Mining and Gold Mining & Exploration. Other services have tailored checklists (for example water permits and drilling for Groundwater Mining, professional and fieldwork approvals for engineering/mapping, facility and goods controls for Warehousing, and data/privacy or transaction requirements for digital services), but country-specific laws and charges are clearly marked unverified rather than guessed. The Kenya view retains these sourced mining-fee benchmarks: KES 1,000 application + KES 10,000 annual fee for the cited small-scale permit, and KES 50,000 application + KES 2,000/ha annual rent for the cited large-scale licence (KES 500,000 minimum). Confirm current applicability with the regulator. The selector's country and territory names reference the [UN Statistics Division M49 country and area list](https://unstats.un.org/unsd/methodology/m49/), with Kosovo included as an additional entry. Space Mining is concept-stage and terrestrial mining permits do not authorize space activity. The page does not present licence charges as mine-development budgets: actual project costs require a defined scope, feasibility work where appropriate, and itemised local quotations. Service estimates, licences, and project costs are separate; no universal or Ateker quote is implied. Country notes were checked on 4 November 2026 and are not legal advice.

## NASA Earth observation data

Open the **Ateker** tab to load NASA POWER daily temperature, corrected precipitation, relative humidity, and wind-speed estimates for ten representative sites spanning Africa, including Madagascar. Each site shows each variable's observation date; the panel also reports the latest valid date, retrieval time, and NASA data-source labels. It requests a recent 45-day range and refreshes no more than every 30 minutes. NASA POWER can lag by several days, so these are delayed daily gridded satellite/reanalysis/model estimates—not instantaneous satellite measurements, ground-station readings, or field measurements. The site samples are not a continuous Africa-wide data grid. Unavailable feeds are reported in the panel rather than replaced with invented live values.

The Ateker workspace also includes a country-atlas-style reference map titled **The Kingdom of Ateker**. It shows reduced geoBoundaries outlines for Uganda, Kenya, South Sudan, and Ethiopia, with an explicitly approximate cultural-region outline and references for Toposa, Nyangatom, Karamoja, Turkana, and Teso. The cultural overlay is illustrative only: it is not an internationally recognized sovereign boundary, a surveyed territorial limit, a land claim, or a mineral-right boundary. Boundary snapshots are dated (Kenya and South Sudan 2020, Uganda 2017, Ethiopia 2016); verify current boundaries and community geography with authoritative local sources.

The map uses a Web Mercator footprint fitted to Africa and Madagascar, NASA GIBS VIIRS Suomi-NPP corrected-reflectance true-colour imagery, and the USGS MRDS occurrence layer. It also queries the USGS MRDS WFS for records in the Africa window and catalogs records whose site-name field is literally `Unknown`, with reported commodity codes, development status, coordinates, and USGS record links. On 3 November 2026, the query returned 3,212 records in that map window, of which 11 used the literal `Unknown` site name. This is a list of unnamed historical database records—not a discovery of unknown deposits or minerals. Their commodity codes do not identify a mineral specimen or allow a refractive index to be assigned.

The map includes broad, explicitly schematic known districts and a reference catalogue of common African mineral species. It gives indicative visible-light refractive-index values for transparent minerals (e.g. diamond, quartz, calcite, fluorite, corundum, beryl, spodumene, zircon, apatite, rutile, and sphalerite) and explains why opaque metal ores and mixed commodities do not have a single useful real refractive index. These are laboratory material properties, not measurements from satellites and not values inferred for a particular deposit. VIIRS true colour is only a backdrop; it cannot detect buried ores or resolve refractive index. Surface mineral mapping needs calibrated multispectral/hyperspectral reflectance (NASA ASTER is a 14-band multispectral instrument; AVIRIS is an airborne hyperspectral instrument), suitable geology/alteration context, and field/laboratory confirmation. NASA's image caption identifies its date and the image uses an Africa-fitted map projection.

The **Services → Geological Mapping → What’s provided** view surfaces the same schematic district list, live unnamed-record query, and optical-property reference for use alongside the mapping service description. Its interactive Africa map supports zoom, pan, client-drawn polygon areas of interest, and export of those polygons as GeoJSON in WGS84 longitude/latitude coordinates. Drawings stay in the current page until cleared or exported; they are not uploaded or saved to a server. The NASA VIIRS true-colour backdrop, historical USGS MRDS layer, and schematic districts are indicative references—not surveyed boundaries, discoveries, or mineral-rights limits. The occurrence list can be filtered by commodity, status, or coordinates; if the USGS query fails, the view reports the error and offers a retry. The **Open Africa map view** button returns to the satellite and occurrence-map context.

The map also marks the user-reported `_NA_` Turkana/Ilemi gold lead at an approximate reference point, with a focus control. The marker is explicitly unverified and is not a deposit boundary, mineral right, or discovery. No assay value was supplied or independently verified, so grade is shown as unavailable rather than fabricated. A regional USGS MRDS WFS query returned no records in its search window; that historical database result is not proof of absence or presence. A defensible assay requires documented, permitted sampling and a traceable laboratory certificate with sample location, method, units, detection limits, laboratory identity, and QA/QC.

The Services panel can be enlarged with its plus/minus controls or popped out into a centered workspace; on narrow screens the popped-out service list and detail area stack vertically. Press Escape or select Restore to return to the compact panel.

USGS says international MRDS records are not systematically updated (updates ceased in 2011); its map and records are historical, may be incomplete, and should be checked against current national geological surveys. Schematic province footprints are not claim boundaries, deposit outlines, reserve estimates, or economic assessments. The optical-property reference links to Ghosh (1999) for calcite/quartz dispersion and the RefractiveIndex.INFO database. NASA service availability and cloud cover can affect imagery. The site's other rotating dashboard values and generated regional canvas remain illustrative content, not live sensor or survey data.

The server stores order state in `data/contracts.sqlite3` by default. Override this with `CONTRACT_DATABASE` and set `PORT` as needed. Expired encrypted contract packages are removed at startup and hourly while the server is running. If the server is stopped, the database stays on disk until it runs again; configure infrastructure-level retention if that is not acceptable. The browser does not send the encryption passphrase to the server or Stripe.

## Production setup

Deploy the Python server behind a correctly configured HTTPS reverse proxy. Set `SITE_BASE_URL` to the exact public HTTPS origin and configure a Stripe webhook endpoint to that origin's `/api/stripe/webhook`; place the live secret key and webhook signing secret only in the server's environment/secret manager. Persist and back up the SQLite database securely, restrict server/database access, and test webhook delivery, failed and delayed payments, database recovery, and duplicate requests before enabling live charges. The fixed price is £26 GBP in `server.py`.

### Connect `turksoil.org`

The domain was checked on 3 November 2026: its nameservers are IONOS (`ui-dns`), the apex resolves to IONOS addresses (`217.160.0.46` and `2001:8d8:100f:f000::200`), and `www.turksoil.org` has no DNS record. The apex currently serves an IONOS "domain registered" placeholder, not this application. The signed-in IONOS account shows a WordPress Grow project on the temporary hostname `turksoil-limited-j8ivmtmrfc.live-website.com`; after the account holder reported verifying the domain contact email, IONOS listed `turksoil.org` as available in the WordPress connect-domain flow. The WordPress site itself is still the default "Hello world!" post, not the custom app. No DNS records or domain connections have been changed.

WordPress.org provides WordPress software, not hosting. The existing WordPress Grow project can host a WordPress site, but this workspace's application is a standalone HTML app plus a Python payment backend; neither has been installed or integrated into that WordPress project. In addition, the payment-enabled backend needs a Python-capable host (or a static/WordPress site plus a separately hosted Python API and reverse proxy). Confirm which site should be published and plan its integration before attaching the production domain. The current IONOS placeholder IP is not known to be the WordPress project or a server for this application; do not point the domain at it as the application host.

Before connecting the domain to WordPress, decide whether publishing the current default WordPress site on `turksoil.org` is intended or whether the custom app should be installed/integrated first. If connecting WordPress now is intended, use the existing IONOS WordPress project's **Connect domain** flow and select `turksoil.org`. If deploying this custom app, confirm a Python-capable host and its public IP/hostname and HTTPS reverse-proxy setup first. Then, in the IONOS DNS settings for `turksoil.org`:

1. Point the apex/root (`@`) A record at the host's confirmed IPv4 address. Configure an AAAA record only if the host explicitly provides a working IPv6 address.
2. Add `www` as a CNAME to `turksoil.org` (or use the exact DNS target required by the host), and configure the host to redirect `www.turksoil.org` to the chosen canonical origin.
3. Keep the existing MX and TXT records unchanged; they are used for domain email and SPF. If the host requires changing any email-related record, verify the impact before doing so.
4. Configure HTTPS certificates for the apex and `www`, then verify both resolve to the intended host and serve the site securely.
5. Set the server environment to `SITE_BASE_URL=https://turksoil.org` and set the Stripe webhook endpoint to `https://turksoil.org/api/stripe/webhook`. Keep Stripe keys only in the server's environment/secret manager.

No domain connection has been completed: although the domain is now selectable in IONOS, the WordPress site currently contains only the default post, while the custom app has not been installed or integrated there. Avoid changing the live domain until its intended destination is confirmed. Do not manually replace DNS with an unconfirmed target. The public DNS records alone are not sufficient to deploy the Python backend or change the site's destination.

### Receive Stripe payouts in Monzo

Monzo is the payout bank account in this setup; Stripe remains the card checkout and payment processor. To route eligible Stripe payouts to Monzo:

1. Sign in to the Stripe Dashboard for the same merchant account used by this server.
2. Open [Stripe payout settings](https://dashboard.stripe.com/settings/money-management) and add or edit the payout bank account.
3. Enter the Monzo account details directly in Stripe's secure Dashboard, then complete any verification Stripe requests. Do not put bank details in this app, its source files, or chat.
4. Confirm the payout account and currency are supported for your Stripe account country, legal business and Monzo account, and check Stripe's payout schedule. Send a small test-mode payment first; test-mode funds are not real deposits. After activating live mode, verify an actual small live payout in Monzo before treating the connection as complete.

This application cannot select or change the payout account through its checkout API. Account linking, identity checks, live-mode activation, payout timing and eligibility must be handled and confirmed in Stripe and Monzo by the account holder.

The downloaded file is encrypted but remains recoverable only with the client's passphrase. A verified payment is not an electronic signature or acceptance of the underlying draft.

## Tests

Run the backend's isolated tests without contacting Stripe:

```powershell
python -m unittest discover -s tests -v
```
