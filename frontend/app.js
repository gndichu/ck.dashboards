async function loadData() {
    const res = await fetch("http://127.0.0.1:8000/api/data");
    return await res.json();
}

function barChart(element, title, categories, values) {
    let chart = echarts.init(document.getElementById(element));
    chart.setOption({
        title: { text: title },
        tooltip: {},
        xAxis: { type: "category", data: categories },
        yAxis: { type: "value" },
        series: [{
            type: "bar",
            data: values
        }]
    });
}

function pieChart(element, title, data) {
    let chart = echarts.init(document.getElementById(element));
    chart.setOption({
        title: { text: title, left: "center" },
        tooltip: { trigger: "item" },
        series: [{
            type: "pie",
            radius: "60%",
            data: data
        }]
    });
}

function lineChart(element, title, categories, values) {
    let chart = echarts.init(document.getElementById(element));
    chart.setOption({
        title: { text: title },
        xAxis: { type: "category", data: categories },
        yAxis: { type: "value" },
        series: [{
            type: "line",
            data: values
        }]
    });
}

loadData().then(data => {
    console.log(data);

    // Auto-detect numeric columns
    let numericCols = Object.keys(data[0]).filter(k => typeof data[0][k] === "number");

    // Auto-detect category columns
    let categoryCols = Object.keys(data[0]).filter(k => typeof data[0][k] === "string");

    // CHART 1: Bar
    const cat1 = categoryCols[0];
    const num1 = numericCols[0];

    barChart(
        "chart1",
        `${num1} by ${cat1}`,
        data.map(d => d[cat1]),
        data.map(d => d[num1])
    );

    // CHART 2: Pie
    const cat2 = categoryCols[1];
    const grouped = {};
    data.forEach(d => grouped[d[cat2]] = (grouped[d[cat2]] || 0) + 1);

    pieChart(
        "chart2",
        `Distribution of ${cat2}`,
        Object.entries(grouped).map(([name, value]) => ({ name, value }))
    );

    // CHART 3: Line Chart
    lineChart(
        "chart3",
        `${num1} Trend`,
        data.map(d => d[cat1]),
        data.map(d => d[num1])
    );
});
