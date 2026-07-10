/* Basispoint shared charts — no dependencies.
   bpCurveChart(el, points, opts)  — yield curve: [{tenor, yield}, ...]
   bpLineChart(el, series, opts)   — time series: [{date, value}, ...]
   Both render an SVG into `el` sized by viewBox (responsive via CSS). */

(function () {
  "use strict";

  const INK = "#122019", SOFT = "#3C4A42", GREEN = "#1E5B43", RULE = "#C7CFC6";

  function smoothPath(P) {
    let d = `M ${P[0][0].toFixed(1)} ${P[0][1].toFixed(1)}`;
    for (let i = 0; i < P.length - 1; i++) {
      const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1],
            p3 = P[Math.min(P.length - 1, i + 2)];
      const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
      const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
      d += ` C ${c1[0].toFixed(1)} ${c1[1].toFixed(1)}, ${c2[0].toFixed(1)} ${c2[1].toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
    }
    return d;
  }

  function range(values, minPad) {
    let lo = Math.min(...values), hi = Math.max(...values);
    const pad = Math.max(minPad, (hi - lo) * 0.18);
    return [lo - pad, hi + pad];
  }

  window.bpCurveChart = function (el, points, opts = {}) {
    const pts = (points || []).filter(p => p.yield != null);
    if (pts.length < 2) { el.innerHTML = "<p class='note'>No data available.</p>"; return; }
    const W = 460, H = 280, X0 = 66, X1 = 422, Y0 = 70, Y1 = 230;
    const [lo, hi] = range(pts.map(p => p.yield), 0.15);
    const x = i => X0 + (i / (pts.length - 1)) * (X1 - X0);
    const y = v => Y1 - (v - lo) / (hi - lo) * (Y1 - Y0);

    let grid = "", glabels = "";
    [80, 130, 180].forEach(gy => {
      grid += `<line x1="48" y1="${gy}" x2="440" y2="${gy}" stroke-dasharray="2 5"/>`;
      const v = lo + (Y1 - gy) / (Y1 - Y0) * (hi - lo);
      glabels += `<text x="14" y="${gy + 4}">${v.toFixed(2)}%</text>`;
    });

    const P = pts.map((p, i) => [x(i), y(p.yield)]);
    let dots = "", vals = "", tls = "";
    pts.forEach((p, i) => {
      const cx = x(i), cy = y(p.yield);
      dots += `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="3.5"/>`;
      const above = cy > 130;
      vals += `<text x="${(cx - 11).toFixed(1)}" y="${(above ? cy - 10 : cy + 19).toFixed(1)}">${p.yield.toFixed(2)}</text>`;
      tls += `<text x="${(cx - 8).toFixed(1)}" y="248">${p.tenor}</text>`;
    });

    el.innerHTML =
      `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${opts.label || "Yield curve"}">
        <g stroke="${RULE}" stroke-width="1">
          <line x1="48" y1="30" x2="48" y2="230"/><line x1="48" y1="230" x2="440" y2="230"/>${grid}
        </g>
        <g fill="${SOFT}" font-size="10">${glabels}${tls}</g>
        <path d="${smoothPath(P)}" fill="none" stroke="${GREEN}" stroke-width="2.5" stroke-linecap="round"/>
        <g fill="${GREEN}">${dots}</g>
        <g fill="${INK}" font-size="10.5" font-weight="500">${vals}</g>
      </svg>`;
  };

  window.bpLineChart = function (el, series, opts = {}) {
    const pts = (series || []).filter(p => p.value != null);
    if (pts.length < 2) {
      el.innerHTML = "<p class='note'>History begins with the first pipeline run — check back in a few days.</p>";
      return;
    }
    const W = 460, H = 240, X0 = 66, X1 = 440, Y0 = 30, Y1 = 195;
    const [lo, hi] = range(pts.map(p => p.value), opts.minPad ?? 0.1);
    const x = i => X0 + (i / (pts.length - 1)) * (X1 - X0);
    const y = v => Y1 - (v - lo) / (hi - lo) * (Y1 - Y0);
    const unit = opts.unit || "%";
    const fmt = v => unit === "bp" ? Math.round(v) + "bp" : v.toFixed(2) + "%";

    let grid = "", glabels = "";
    [60, 112, 164].forEach(gy => {
      grid += `<line x1="48" y1="${gy}" x2="440" y2="${gy}" stroke-dasharray="2 5"/>`;
      const v = lo + (Y1 - gy) / (Y1 - Y0) * (hi - lo);
      glabels += `<text x="8" y="${gy + 4}">${fmt(v)}</text>`;
    });

    const P = pts.map((p, i) => [x(i), y(p.value)]);
    const line = P.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
    const last = P[P.length - 1];
    const short = d => d ? d.slice(5) : "";  // YYYY-MM-DD -> MM-DD

    el.innerHTML =
      `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${opts.label || "Time series"}">
        <g stroke="${RULE}" stroke-width="1">
          <line x1="48" y1="20" x2="48" y2="195"/><line x1="48" y1="195" x2="440" y2="195"/>${grid}
        </g>
        <g fill="${SOFT}" font-size="10">
          ${glabels}
          <text x="50" y="212">${short(pts[0].date)}</text>
          <text x="404" y="212">${short(pts[pts.length - 1].date)}</text>
        </g>
        <path d="${line}" fill="none" stroke="${GREEN}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="3.5" fill="${GREEN}"/>
        <text x="${Math.min(last[0] + 8, 415).toFixed(1)}" y="${(last[1] - 8).toFixed(1)}" fill="${INK}" font-size="10.5" font-weight="500">${fmt(pts[pts.length - 1].value)}</text>
      </svg>`;
  };
})();