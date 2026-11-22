# Transit Receipt

Save bus arrival estimates and compare them with later, explicitly labelled vehicle encounters at selected stops.

Open https://coolcode.ca/transitreceipt/.

<!-- coolcode:guide -->
Start with a Halifax stop, then choose a saved prediction receipt. A positive difference means the first retained vehicle sighting was later than the estimate. A missing sighting stays unmatched; it never becomes an on-time arrival.
<!-- /coolcode:guide -->

## Collection

Halifax is enabled immediately without a key. Selected stop IDs are listed in `config.json`: Barrington/Duke, Spring Garden/South Park, Water Street Terminal, and one bay at each of Mumford and Bridge terminals. This is a selected-stop sample, not comprehensive coverage.

To enable Langley, add the repository Actions secret **TRANSLINK_API_KEY** using your TransLink developer key, then run the workflow. The collector resolves Carvolth Exchange platform stops from TransLink’s current static GTFS. It never writes the key into receipts, the site, or logs. Do not paste a key into public configuration.

The collector keeps predictions 30 seconds to 30 minutes ahead. Feed timestamps must be no more than five minutes old; vehicle reports no more than two minutes old. Matching requires agency, trip ID, explicit service date, trip start time, stop ID and stop sequence.

Outcome evidence is either an explicit `STOPPED_AT` report or a vehicle within 60 m of the stop travelling at most 1.5 m/s with a supplied speed. The earliest retained sighting after a prediction capture is used. GPS encounters are estimates, not confirmed arrivals or door openings. Traffic signals, dwell time and missing data can affect them. Predictions for cancelled/skipped/no-data events are excluded when marked at capture. Later cancellations do not retroactively erase the earlier prediction; it remains unmatched unless an encounter is actually recorded.

Minute polling in short hourly windows misses many arrivals. A missing result does not mean the bus did not arrive. For sustained monitoring, run the same script on a server at the allowed provider cadence and commit new receipts before publishing.

Schedule: **Hourly at minute 13, with ten samples one minute apart (UTC)**. GitHub schedules are best effort, not a precise timer. Scheduled and manual runs collect; code pushes and pull requests only validate/build the saved archive.

```sh
python3 -m pip install -r requirements.txt
python3 scripts/collect.py --samples 10 --interval 60
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

The default build is offline. Collectors validate before saving; failed collection does not replace the good deployment. All dated normalized receipts are permanent tracked files under `archive/YYYY-MM/*.json.gz`. Each includes the capture time, source URL, SHA-256 of the downloaded response, selected values and provenance. These files preserve the selected data, not necessarily the full upstream response. Identical receipts deduplicate; old receipts are never overwritten. No Zenodo configuration is needed.

The dashboard loads the most recent 14 days of captures. Older receipts remain downloadable through `data/archive.json` and retained in Git history. The archive is the durable record; Actions artifact retention is unrelated. Observation revisions remain in their dated source receipts; the dashboard uses the latest reading (or earliest stop encounter for transit). CSV export covers the selected receipt and filter. JSON and individual compressed receipt downloads preserve source links.

## Interpretation

A blank score means outcomes are missing, not zero error. A selected receipt's mean absolute difference is the mean of absolute matched differences; signed bias retains direction. Different receipts can refer to the same outcome, so points across receipts are not independent events. Live lead time is measured from capture to target.

## Publishing and monitoring

The main workflow checks models, collection logic, the static builder and browser behaviour, then commits new source receipts before deploying. Set repository Pages source to **GitHub Actions**. PRs cannot collect, commit or deploy. No Cloudflare Worker changes are required.

Optionally add an Actions secret **HEALTHCHECKS_PING_URL**. Scheduled/manual collection sends start/success/failure pings; the collector itself does not send email or accuracy reports. Match the Healthchecks schedule to the cron above and allow enough grace for GitHub queue delays (90 minutes is reasonable). A success ping confirms archive collection and commit; it does not certify forecast accuracy or Pages deployment.

The ten-minute transit sample requires a grace period longer than its execution time. Optional monitoring is inactive without the secret. The site reports the last successful collection and marks it overdue when stale.

## Privacy

Visitors load public saved data from this site. Filtering and CSV export run in the browser without accounts, storage or upstream API calls. The shared CoolCode counter records aggregate page opens without filter values. Source collection happens in GitHub Actions.

## Sources and attribution

Halifax source: https://www.halifax.ca/transportation/halifax-transit/transit-technology/general-transit-feed-gtfs

Contains information licensed under the Open Government Licence — Halifax.

TransLink developer registration and terms: https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources

GTFS-Realtime reference: https://gtfs.org/documentation/realtime/reference/

## Software

Application code is MIT licensed. Upstream datasets retain their original licences. Browser screenshots are saved as seven-day CI artifacts; all data receipts remain in the repository.
