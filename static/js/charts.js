// Render the report's charts with Chart.js using data embedded by the server.
(function () {
    const dataEl = document.getElementById("report-data");
    if (!dataEl) return;

    let report;
    try {
        report = JSON.parse(dataEl.textContent);
    } catch (e) {
        console.error("Could not parse report data", e);
        return;
    }

    const PRIMARY = "#6c8cff";
    const PALETTE = [
        "#6c8cff", "#8b6cff", "#ff6b7a", "#ffc878",
        "#78dcaa", "#5fd0d8", "#ff9ecb", "#c3d0ff",
    ];

    const baseOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
            x: { ticks: { color: "#9aa0c0" }, grid: { color: "#2c3258" } },
            y: { ticks: { color: "#9aa0c0" }, grid: { color: "#2c3258" }, beginAtZero: true },
        },
    };

    function barChart(canvasId, labels, counts, colorByBar) {
        const el = document.getElementById(canvasId);
        if (!el) return;
        new Chart(el, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    backgroundColor: colorByBar
                        ? labels.map((_, i) => PALETTE[i % PALETTE.length])
                        : PRIMARY,
                    borderRadius: 4,
                }],
            },
            options: baseOptions,
        });
    }

    function lineChart(canvasId, labels, counts) {
        const el = document.getElementById(canvasId);
        if (!el) return;
        new Chart(el, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    data: counts,
                    borderColor: PRIMARY,
                    backgroundColor: "rgba(108,140,255,0.2)",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                }],
            },
            options: baseOptions,
        });
    }

    if (report.time_series) {
        lineChart("timeSeriesChart", report.time_series.labels, report.time_series.counts);
    }

    (report.categorical_summary || []).forEach((cat, i) => {
        barChart(`cat-${i + 1}`, cat.labels, cat.counts, true);
    });

    (report.histograms || []).forEach((h, i) => {
        barChart(`hist-${i + 1}`, h.labels, h.counts, false);
    });
})();
