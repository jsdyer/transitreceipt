export default {
  "kind": "transit",
  "unit": "min",
  "accent": "#334db4",
  "tint": "#e8ecfb",
  "staleHours": 4,
  "text": {
    "eyebrow": "ARCHIVED BUS PREDICTIONS",
    "entity-label": "Agency / stop",
    "bias-help": "Positive = sighting later than the estimate",
    "mae-label": "Mean absolute sighting difference",
    "bias-label": "Mean sighting delay",
    "cadence": "Hourly collection windows: ten samples, one minute apart. Halifax runs without a key. TransLink activates when TRANSLINK_API_KEY is set in GitHub Actions. This samples service; it does not monitor every arrival.",
    "observed-heading": "First stop sighting",
    "target-heading": "Predicted arrival (UTC)",
    "difference-heading": "Sighting − prediction",
    "obs-legend": "Stop sighting",
    "matched-help": "Predictions linked to a later stop encounter"
  },
  "method": [
    "The collector saves future GTFS-Realtime arrival estimates for selected Halifax stops. With a TransLink API key, it also watches Carvolth Exchange stops resolved from TransLink’s static feed. A trip, service date, start time, stop and stop sequence identify each event.",
    "An outcome is a fresh vehicle report explicitly marked STOPPED_AT, or a slow vehicle within 60 metres of the configured stop. The latter is labelled GPS encounter. Neither is an exact door-opening timestamp: a nearby traffic signal or a long dwell can affect the comparison.",
    "Only sightings after the receipt was captured can match it. The earliest retained sighting is used. Missing vehicles, feed gaps and cancelled or skipped stops are not counted as successful arrivals. A disappearing prediction is never treated as an observation.",
    "Minute polling during short hourly windows misses many arrivals and can introduce delay in the first sighting. These are sampled comparisons, not an agency-wide punctuality score. The archive keeps unmatched predictions too.",
    "Contains information licensed under the Open Government Licence — Halifax. Optional TransLink collection uses its Open API terms. The API key stays in GitHub Actions and is never published or requested from visitors."
  ],
  "sources": [
    {
      "label": "Halifax GTFS and real-time data",
      "url": "https://www.halifax.ca/transportation/halifax-transit/transit-technology/general-transit-feed-gtfs"
    },
    {
      "label": "GTFS-Realtime field definitions",
      "url": "https://gtfs.org/documentation/realtime/reference/"
    },
    {
      "label": "TransLink developer registration",
      "url": "https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources"
    },
    {
      "label": "Repository setup and collection scope",
      "url": "https://github.com/jsdyer/transitreceipt#collection"
    }
  ],
  "chartCaption": "Each point is a predicted stop visit. Dots are later vehicle encounters, not confirmed door-open arrival records.",
  "tableNote": "Sightings are estimates; repeated forecasts of the same visit are not independent arrivals.",
  "id": "transitreceipt"
};
