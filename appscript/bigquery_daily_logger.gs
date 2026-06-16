/**
 * EdmontonLens — BigQuery Daily Logger (Google Apps Script)
 * ---------------------------------------------------------------------------
 * Paste this into Google Apps Script (https://script.google.com), bound to a
 * Google Sheet. Enable the "BigQuery API" advanced service
 * (Services + > BigQuery API) and set a daily time-driven trigger on
 * runDailySummary().
 *
 * It queries the public/owned `edmonton_lens` BigQuery dataset for:
 *   1. Yesterday's city-wide average transit on-time rate.
 *   2. Top 3 and bottom 3 neighbourhoods by overall score.
 *   3. Count of high-risk routes (delay probability > 0.7).
 * Writes everything to a sheet and emails the owner a summary.
 *
 * Replace PROJECT_ID with your GCP project that hosts the dataset.
 */

const PROJECT_ID = 'YOUR_GCP_PROJECT_ID';
const DATASET = 'edmonton_lens';
const SHEET_NAME = 'Daily Summary';

/**
 * Entry point — wire a daily trigger to this function.
 */
function runDailySummary() {
  const start = new Date();
  const sheet = getOrCreateSheet_(SHEET_NAME);

  const onTime = queryCityWideOnTimeRate_();
  const ranked = queryNeighbourhoodExtremes_();
  const highRisk = queryHighRiskRouteCount_();

  const timestamp = Utilities.formatDate(start, Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
  writeSummary_(sheet, timestamp, onTime, ranked, highRisk);

  const durationMs = new Date().getTime() - start.getTime();
  const rowCount = 1 + ranked.top.length + ranked.bottom.length;
  Logger.log('runDailySummary complete in %s ms, wrote %s summary rows', durationMs, rowCount);

  emailOwner_(timestamp, onTime, ranked, highRisk, durationMs);
}

/**
 * Run an arbitrary standard-SQL query and return its rows.
 * @param {string} sql
 * @return {Array<Object>} array of {fields, rows}
 */
function runQuery_(sql) {
  const request = { query: sql, useLegacySql: false };
  let queryResults = BigQuery.Jobs.query(request, PROJECT_ID);
  const jobId = queryResults.jobReference.jobId;

  // Poll until the query completes.
  let sleepTimeMs = 500;
  while (!queryResults.jobComplete) {
    Utilities.sleep(sleepTimeMs);
    sleepTimeMs = Math.min(sleepTimeMs * 2, 5000);
    queryResults = BigQuery.Jobs.getQueryResults(PROJECT_ID, jobId);
  }
  return queryResults.rows || [];
}

/**
 * @return {number} yesterday's city-wide average on-time rate (0..1), or -1.
 */
function queryCityWideOnTimeRate_() {
  const sql =
    'SELECT AVG(on_time_rate) AS avg_on_time ' +
    'FROM `' + PROJECT_ID + '.' + DATASET + '.transit_performance` ' +
    'WHERE service_date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)';
  const rows = runQuery_(sql);
  if (rows.length === 0 || rows[0].f[0].v === null) {
    return -1;
  }
  return parseFloat(rows[0].f[0].v);
}

/**
 * @return {{top: Array, bottom: Array}} top/bottom 3 neighbourhoods by score.
 */
function queryNeighbourhoodExtremes_() {
  const base =
    'SELECT neighbourhood_id, overall_score ' +
    'FROM `' + PROJECT_ID + '.' + DATASET + '.neighbourhood_kpis` ' +
    'WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM `' +
    PROJECT_ID + '.' + DATASET + '.neighbourhood_kpis`) ';

  const topRows = runQuery_(base + 'ORDER BY overall_score DESC LIMIT 3');
  const bottomRows = runQuery_(base + 'ORDER BY overall_score ASC LIMIT 3');

  const map = function (rows) {
    return rows.map(function (r) {
      return { id: r.f[0].v, score: parseFloat(r.f[1].v) };
    });
  };
  return { top: map(topRows), bottom: map(bottomRows) };
}

/**
 * @return {number} count of routes with predicted delay probability > 0.7.
 */
function queryHighRiskRouteCount_() {
  const sql =
    'SELECT COUNT(DISTINCT route_id) AS high_risk ' +
    'FROM `' + PROJECT_ID + '.' + DATASET + '.delay_predictions` ' +
    'WHERE prediction_date = (SELECT MAX(prediction_date) FROM `' +
    PROJECT_ID + '.' + DATASET + '.delay_predictions`) ' +
    'AND delay_probability > 0.7';
  const rows = runQuery_(sql);
  if (rows.length === 0 || rows[0].f[0].v === null) {
    return 0;
  }
  return parseInt(rows[0].f[0].v, 10);
}

/**
 * Get (or create + header) the target sheet.
 */
function getOrCreateSheet_(name) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  if (sheet.getLastRow() === 0) {
    sheet
      .appendRow([
        'Timestamp',
        'City On-Time Rate',
        'Top Neighbourhoods',
        'Bottom Neighbourhoods',
        'High-Risk Routes (>0.7)',
      ])
      .getRange(1, 1, 1, 5)
      .setFontWeight('bold');
  }
  return sheet;
}

/**
 * Append a formatted summary row.
 */
function writeSummary_(sheet, timestamp, onTime, ranked, highRisk) {
  const fmtList = function (arr) {
    return arr
      .map(function (n) {
        return n.id + ' (' + n.score.toFixed(2) + ')';
      })
      .join(', ');
  };
  const onTimeDisplay = onTime >= 0 ? (onTime * 100).toFixed(1) + '%' : 'n/a';
  sheet.appendRow([
    timestamp,
    onTimeDisplay,
    fmtList(ranked.top),
    fmtList(ranked.bottom),
    highRisk,
  ]);
}

/**
 * Email the sheet owner a plain-text digest.
 */
function emailOwner_(timestamp, onTime, ranked, highRisk, durationMs) {
  const owner = Session.getEffectiveUser().getEmail();
  if (!owner) {
    return;
  }
  const onTimeDisplay = onTime >= 0 ? (onTime * 100).toFixed(1) + '%' : 'n/a';
  const body =
    'EdmontonLens Daily Summary (' + timestamp + ')\n\n' +
    'City-wide transit on-time rate (yesterday): ' + onTimeDisplay + '\n\n' +
    'Top neighbourhoods:\n  ' +
    ranked.top.map(function (n) { return n.id + ': ' + n.score.toFixed(2); }).join('\n  ') +
    '\n\nBottom neighbourhoods:\n  ' +
    ranked.bottom.map(function (n) { return n.id + ': ' + n.score.toFixed(2); }).join('\n  ') +
    '\n\nHigh-risk routes (delay prob > 0.7): ' + highRisk +
    '\n\nGenerated in ' + durationMs + ' ms by the EdmontonLens BigQuery logger.';

  MailApp.sendEmail(owner, 'EdmontonLens Daily Summary — ' + timestamp, body);
}
