"use strict";

const $ = (id) => document.getElementById(id);
const form = $("pricing-form");
const money = (value, digits = 2) => new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", minimumFractionDigits: digits, maximumFractionDigits: digits,
}).format(value);
const numeric = (value, digits = 4) => Number(value).toFixed(digits);
// Whole-dollar inputs read better without cents ("$100 strike" rather than "$100.00 strike").
const inputMoney = (value) => money(value, Number.isInteger(value) ? 0 : 2);
const plural = (count, word) => `${count.toLocaleString("en-US")} ${word}${count === 1 ? "" : "s"}`;
let result = null;
let activeChart = "payoff";
let controller;
let requestId = 0;

function readInputs() {
  return Object.fromEntries([...new FormData(form)].map(([key, value]) => [key,
    key === "option_type" ? value : Number(value)]));
}

function setStale(stale) {
  $("results").dataset.stale = String(stale);
  $("download-button").disabled = stale || !result;
}

function renderResult(data) {
  const {inputs, greeks, monte_carlo: mc} = data;
  $("price").textContent = money(data.price);
  const type = inputs.option_type === "call" ? "Call" : "Put";
  $("scenario-title").textContent = `${type} option, ${inputMoney(inputs.strike_price)} strike`;
  $("scenario-summary").textContent = `Stock at ${inputMoney(inputs.stock_price)}, ${plural(inputs.days, "day")} to expiry, ${numeric(inputs.volatility_percent, 2).replace(/\.?0+$/, "")}% volatility, ${numeric(inputs.rate_percent, 2).replace(/\.?0+$/, "")}% risk-free rate.`;
  $("break-even").textContent = money(data.break_even);
  $("mc-price").textContent = money(mc.price);
  const difference = mc.price - data.price;
  $("mc-difference").textContent = Math.abs(difference) < 0.00005
    ? "Same as Black–Scholes"
    : `${money(Math.abs(difference), 4)} ${difference > 0 ? "above" : "below"} Black–Scholes`;
  $("mc-interval").textContent = `${money(mc.confidence_low, 4)} to ${money(mc.confidence_high, 4)}`;
  $("mc-error").textContent = `Standard error ${money(mc.standard_error, 4)} from ${plural(mc.simulations, "path")}.`;
  $("mc-warning").textContent = data.monte_carlo_warning || "";
  $("mc-warning").hidden = !data.monte_carlo_warning;
  $("iv").textContent = data.implied_volatility === null ? "Unavailable" : `${numeric(data.implied_volatility * 100, 2)}%`;
  $("iv-note").textContent = data.implied_volatility === null
    ? `No volatility gives a price of ${money(inputs.market_price)}.`
    : `The volatility that prices this option at ${money(inputs.market_price)}.`;
  $("iv-warning").textContent = data.iv_error || "";
  $("iv-warning").hidden = !data.iv_error;
  $("iv-bounds").textContent = `${money(data.price_bounds[0])} to ${money(data.price_bounds[1])}`;
  for (const [key, value] of Object.entries(greeks)) $("greek-" + key).textContent = numeric(value);
  renderChart();
}

async function calculate() {
  if (!form.reportValidity()) return;
  const id = ++requestId;
  controller?.abort();
  controller = new AbortController();
  const thisController = controller;
  const inputSnapshot = readInputs();
  $("request-error").hidden = true;
  $("calculate-button").disabled = true;
  $("calculate-button").textContent = "Calculating…";
  $("results").setAttribute("aria-busy", "true");
  $("status").textContent = "Calculating…";
  $("download-button").disabled = true;
  const timeout = setTimeout(() => thisController.abort(), 25000);
  try {
    const response = await fetch("/api/calculate", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify(inputSnapshot), signal: thisController.signal,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to calculate this scenario.");
    if (id !== requestId) return;
    result = data;
    renderResult(data);
    const dirty = JSON.stringify(readInputs()) !== JSON.stringify(inputSnapshot);
    setStale(dirty);
    $("status").textContent = dirty ? "Inputs changed. Calculate to update." : "Up to date";
  } catch (error) {
    if (id !== requestId) return;
    $("request-error").textContent = error.name === "AbortError"
      ? "The calculation took more than 25 seconds. Try fewer Monte Carlo paths, then calculate again."
      : error instanceof SyntaxError || error instanceof TypeError
        ? "The pricing service could not be reached. Check your connection, then calculate again."
        : error.message;
    $("request-error").hidden = false;
    $("status").textContent = "Calculation failed";
    if (result) setStale(true);
    else $("scenario-summary").textContent = "No scenario calculated yet";
  } finally {
    clearTimeout(timeout);
    if (id === requestId) {
      $("calculate-button").disabled = false;
      $("calculate-button").textContent = "Calculate";
      $("results").setAttribute("aria-busy", "false");
    }
  }
}

function chartData() {
  const {inputs} = result;
  const stockMarkers = [{label: "Strike", value: inputs.strike_price}, {label: "Today", value: inputs.stock_price}];
  if (activeChart === "volatility") {
    const markers = [{label: "Input", value: inputs.volatility_percent, unit: "%"}];
    if (result.implied_volatility !== null) markers.push({label: "Implied", value: result.implied_volatility * 100, unit: "%"});
    return {rows: result.volatility_sensitivity, x: "volatility", xLabel: "Volatility (%)",
      series: [{key: "option_price", label: "Option price", color: "#0a84ff"}],
      description: "Theoretical option price as volatility changes.", markers};
  }
  if (activeChart === "greeks") {
    const greek = $("selected-greek").value;
    return {rows: result.stock_sensitivity, x: "stock_price", xLabel: "Stock price ($)",
      series: [{key: greek, label: greek, color: "#0a84ff"}],
      description: `${greek} across stock prices, with other inputs unchanged.`, markers: stockMarkers, dotAt: inputs.stock_price};
  }
  return {rows: result.stock_sensitivity, x: "stock_price", xLabel: "Stock price ($)",
    series: [{key: "option_price", label: "Option value today", color: "#0a84ff"},
      {key: "profit_loss", label: "Profit or loss at expiry", color: "#ff2d78"}],
    description: "Option value today and profit or loss at expiry, across stock prices.",
    markers: [...stockMarkers, {label: "Break-even", value: result.break_even}], dotAt: inputs.stock_price};
}

function svgElement(tag, attributes, content) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, String(value));
  if (content !== undefined) node.textContent = content;
  return node;
}

// Markers at the same price share one label; nearby labels alternate sides and step down a row.
function layoutMarkers(markers, px, minX, maxX) {
  const placed = [];
  for (const marker of markers.filter(m => m.value >= minX && m.value <= maxX).map(m => ({...m, x: px(m.value)})).sort((a, b) => a.x - b.x)) {
    const last = placed[placed.length - 1];
    if (last && Math.abs(last.x - marker.x) < 1) last.label += ` and ${marker.label.toLowerCase()}`;
    else placed.push(marker);
  }
  let run = 0;
  placed.forEach((marker, index) => {
    run = index > 0 && marker.x - placed[index - 1].x < 130 ? run + 1 : 0;
    marker.anchor = run % 2 === 0 ? "end" : "start";
    marker.row = Math.floor(run / 2) % 2;
  });
  return placed;
}

function renderChart() {
  if (!result) return;
  const {rows, x, xLabel, series, description, markers, dotAt} = chartData();
  $("chart-description").textContent = description;
  $("greek-picker").hidden = activeChart !== "greeks";
  $("chart-panel").setAttribute("aria-labelledby", "tab-" + activeChart);
  $("chart-tooltip").hidden = true;
  const legend = $("chart-legend");
  legend.replaceChildren(...series.map((s, index) => {
    const span = document.createElement("span");
    span.className = "legend-item" + (index ? " secondary" : "");
    span.textContent = s.label;
    return span;
  }));
  const svg = $("chart");
  svg.replaceChildren(svgElement("title", {}, description));
  svg.setAttribute("aria-label", description + " Exact values are in the data table below the chart.");
  const left = 66, right = 876, top = 44, bottom = 290;
  const minX = rows[0][x], maxX = rows[rows.length - 1][x];
  const allY = rows.flatMap(row => series.map(s => row[s.key]));
  let minY = Math.min(...allY), maxY = Math.max(...allY);
  const pad = (maxY - minY || Math.max(Math.abs(maxY), 1)) * 0.08;
  minY -= pad; maxY += pad;
  const px = v => left + (v - minX) / (maxX - minX) * (right - left);
  const py = v => bottom - (v - minY) / (maxY - minY) * (bottom - top);
  const tick = v => new Intl.NumberFormat("en-US", {maximumFractionDigits: activeChart === "greeks" ? 3 : 2, notation: Math.abs(v) >= 10000 ? "compact" : "standard"}).format(v);
  for (let i = 0; i <= 4; i++) {
    const value = minY + (maxY - minY) * i / 4;
    svg.append(svgElement("line", {x1:left, x2:right, y1:py(value), y2:py(value), class:"chart-grid"}));
    svg.append(svgElement("text", {x:left-12, y:py(value)+4, "text-anchor":"end", class:"chart-axis"}, tick(value)));
  }
  if (minY < 0 && maxY > 0) svg.append(svgElement("line", {x1:left, x2:right, y1:py(0), y2:py(0), class:"chart-zero", "stroke-dasharray":"4"}));
  for (let i = 0; i <= 5; i++) {
    const value = minX + (maxX - minX) * i / 5;
    svg.append(svgElement("text", {x:px(value), y:bottom+22, "text-anchor":"middle", class:"chart-axis"}, tick(value)));
  }
  svg.append(svgElement("text", {x:(left+right)/2, y:335, "text-anchor":"middle", class:"chart-axis"}, xLabel));
  for (const marker of layoutMarkers(markers, px, minX, maxX)) {
    const labelY = 14 + marker.row * 16;
    const value = marker.unit === "%" ? `${numeric(marker.value, 2)}%` : inputMoney(Math.round(marker.value * 100) / 100);
    svg.append(svgElement("line", {x1:marker.x, x2:marker.x, y1:labelY + 4, y2:bottom, class:"chart-marker"}));
    svg.append(svgElement("text", {x:marker.x + (marker.anchor === "end" ? -6 : 6), y:labelY, "text-anchor":marker.anchor, class:"chart-marker-label"}, `${marker.label} ${value}`));
  }
  for (const s of series) svg.append(svgElement("polyline", {
    points:rows.map(row => `${px(row[x])},${py(row[s.key])}`).join(" "), class:"chart-line", stroke:s.color,
  }));
  if (dotAt !== undefined) {
    const nearest = rows.reduce((best, row) => Math.abs(row[x] - dotAt) < Math.abs(best[x] - dotAt) ? row : best);
    svg.append(svgElement("circle", {cx:px(nearest[x]), cy:py(nearest[series[0].key]), r:5.5, fill:series[0].color, class:"chart-dot"}));
  }
  const hoverLine = svgElement("line", {x1:0, x2:0, y1:top, y2:bottom, class:"chart-hover", visibility:"hidden"});
  svg.append(hoverLine);
  svg.onpointermove = event => {
    const bounds = svg.getBoundingClientRect();
    const svgX = (event.clientX - bounds.left) / bounds.width * 900;
    if (svgX < left || svgX > right) { hoverLine.setAttribute("visibility", "hidden"); $("chart-tooltip").hidden = true; return; }
    const index = Math.round((svgX - left) / (right - left) * (rows.length - 1));
    const row = rows[Math.max(0, Math.min(rows.length-1, index))];
    hoverLine.setAttribute("x1", px(row[x])); hoverLine.setAttribute("x2", px(row[x]));
    hoverLine.setAttribute("visibility", "visible");
    $("chart-tooltip").textContent = `${xLabel}: ${numeric(row[x], 2)}\n` + series.map(s => `${s.label}: ${numeric(row[s.key], 4)}`).join("\n");
    $("chart-tooltip").hidden = false;
  };
  svg.onpointerleave = () => { hoverLine.setAttribute("visibility", "hidden"); $("chart-tooltip").hidden = true; };
  const table = $("chart-table");
  table.replaceChildren();
  const head = table.createTHead().insertRow();
  for (const label of [xLabel, ...series.map(s => s.label)]) {
    const th = document.createElement("th"); th.scope = "col"; th.textContent = label; head.append(th);
  }
  const body = table.createTBody();
  for (const row of rows) {
    const tr = body.insertRow();
    for (const value of [row[x], ...series.map(s => row[s.key])]) tr.insertCell().textContent = numeric(value);
  }
}

function activateTab(tab, focus = false) {
  activeChart = tab.dataset.chart;
  document.querySelectorAll("[data-chart]").forEach(button => {
    const selected = button === tab;
    button.setAttribute("aria-selected", String(selected)); button.tabIndex = selected ? 0 : -1;
  });
  if (focus) tab.focus();
  renderChart();
}

form.addEventListener("submit", event => { event.preventDefault(); calculate(); });
form.addEventListener("input", () => {
  setStale(true);
  $("status").textContent = "Inputs changed. Calculate to update.";
});
form.addEventListener("reset", () => {
  setStale(true);
  $("status").textContent = "Resetting…";
  setTimeout(calculate, 0);
});
const tabs = [...document.querySelectorAll("[data-chart]")];
for (const tab of tabs) {
  tab.addEventListener("click", () => activateTab(tab));
  tab.addEventListener("keydown", event => {
    const index = tabs.indexOf(tab);
    const next = event.key === "ArrowRight" ? (index+1)%tabs.length
      : event.key === "ArrowLeft" ? (index+tabs.length-1)%tabs.length
      : event.key === "Home" ? 0 : event.key === "End" ? tabs.length-1 : null;
    if (next !== null) { event.preventDefault(); activateTab(tabs[next], true); }
  });
}
$("selected-greek").addEventListener("change", renderChart);
$("download-button").addEventListener("click", () => {
  if (!result || $("results").dataset.stale === "true") return;
  const chart = chartData();
  const metadata = {...result.inputs, black_scholes_price:result.price, ...result.greeks,
    monte_carlo_price:result.monte_carlo.price, standard_error:result.monte_carlo.standard_error,
    confidence_low:result.monte_carlo.confidence_low, confidence_high:result.monte_carlo.confidence_high,
    monte_carlo_warning:result.monte_carlo_warning,
    implied_volatility:result.implied_volatility, iv_error:result.iv_error, break_even:result.break_even};
  const metaKeys = Object.keys(metadata);
  const chartKeys = [chart.x, ...chart.series.map(s => s.key)];
  const escape = value => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const lines = [[...metaKeys, ...chartKeys].map(escape).join(","),
    ...chart.rows.map(row => [...metaKeys.map(k => metadata[k]), ...chartKeys.map(k => row[k])].map(escape).join(","))];
  const url = URL.createObjectURL(new Blob([lines.join("\r\n")], {type:"text/csv;charset=utf-8"}));
  const link = document.createElement("a"); link.href = url; link.download = `options-${result.inputs.option_type}-${activeChart}.csv`;
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});

const compactLayout = window.matchMedia("(max-width: 800px)");
const scenarioSettings = $("scenario-settings");
function syncScenarioSettings() {
  scenarioSettings.open = !compactLayout.matches;
}
compactLayout.addEventListener("change", syncScenarioSettings);
syncScenarioSettings();

calculate();
