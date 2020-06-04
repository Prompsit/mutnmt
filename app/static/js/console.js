$(document).ready(function() {
    let engine_id = $("#engine_id").val();
    let engine_stopped = false;

    const interval = 1000;

    let setupTimer = (el) => {
        let timestamp = parseInt($(el).attr("data-started"));
        let begin = moment();
        let end = moment.unix(timestamp).add($(el).attr("data-minutes"), 'minutes');
        let duration = moment.duration(end.diff(begin))

        $(el).html(moment.utc(duration.asMilliseconds()).format("mm:ss"))
    }

    $(".time-left").each(function(i, el) {
        setupTimer(el)
        setInterval(() => {
            setupTimer(el)
        }, interval);
    });

    let make_chart = (element, chart_data) => {
        let chart = new ApexCharts(element, {
            series: [{
                name: chart_data.y,
                data: Array.from(Array(250), (_, i) => [i, 0])
            }],
            chart: {
                id: chart_data.id,
                group: 'training',
                type: 'area',
                stacked: false,
                height: 400,
                zoom: {
                    type: 'x',
                    enabled: true,
                    autoScaleYaxis: true
                },
                toolbar: {
                    autoSelected: 'zoom'
                }
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    inverseColors: false,
                    opacityFrom: 0.5,
                    opacityTo: 0,
                    stops: [0, 90, 100]
                },
            },
            dataLabels: { enabled: false },
            yaxis: { 
                title: { text: chart_data.y },
                labels: {
                    formatter: (val) => {
                        if (val % parseInt(val) == 0) return parseInt(val)
                        return val.toFixed(8)
                    },

                    minWidth: 40
                }
            },
            xaxis: {
                title: {text : chart_data.x },
                tickAmount: 10,
            },
            tooltip: {
                shared: true
            }
        });

        return chart;
    };

    const chart_metadata = {
        "train/train_batch_loss": { x: "Steps", y: "Batch loss", id: "train_batch_loss", last: 0 },
        "train/train_learning_rate": { x: "Steps", y: "Learning rate", id: "train_learning_rate", last: 0 },
        "valid/valid_loss": { x: "Steps", y: "Batch loss", id: "valid_loss", last: 0 },
        "valid/valid_score": { x: "Steps", y: "Score", id: "valid_score", last: 0 }
    }

    let chart_series = {
        "train/train_batch_loss": [],
        "train/train_learning_rate": [],
        "valid/valid_loss": [],
        "valid/valid_score": []
    }

    let charts = {}
    $(".training-chart").each(function(i, e) {
        let tag = $(this).attr("data-tag");
        let chart = make_chart(e, chart_metadata[tag])
        charts[tag] = chart;
        chart.render();
    });

    longpoll(5000, {
        url: `../graph_data`,
        method: "post",
        data: {
            tags: Object.keys(chart_metadata),
            id: engine_id,
            last: JSON.stringify(Object.keys(chart_metadata).reduce((obj, x) => { obj[x] = chart_metadata[x].last; return obj }, {}))
        }
    }, function(data) {
        $(".training-chart").each(function(i, e) {
            let tag = $(this).attr("data-tag");
            if (data) {
                let { stats, stopped } = data
                let tag_stats = stats[tag];
                if (tag_stats) {
                    for (stat of tag_stats) {
                        if (!(stat.step in chart_series[tag].map((v) => v[0]))) {
                            if (!stopped && chart_series[tag].length > 250) {
                                chart_series[tag].shift()
                            }

                            chart_series[tag].push([stat.step, stat.value])
                            chart_metadata[tag].last = stat.step
                        }
                    }

                    charts[tag].updateSeries([{ data: chart_series[tag].map((v) => v) }]);
                }
            }
        });

        // We don't keep longpolling if training is done
        if (data.stopped) return false
    }, true);

    /* Train status */
    longpoll(5000, {
        url: `../train_status`,
        method: "post",
        data: {
            id: engine_id
        }
    }, (data) => {
        if (data.stats && data.stats['done'] && data.stopped == false) {
            window.location.href = `../finish/${engine_id}`
        }

        if (data.stats && data.stats['epoch']) {
            $(".epoch-no").html(data.stats['epoch'])
        }

        if (data.power) {
            $(".gpu-power").html(data.power);
        }

        if (data.power_reference) {
            $(".power-reference").html("");
            for (power_ref of data.power_reference) {
                $(".power-reference").html($(".power-reference").html() + `${power_ref}<br />`)
            }
        }

        // We don't keep longpolling if training is done
        engine_stopped = data.stopped
        if (data.stopped) return false
    }, true);

    /* Train log */
    let log_table = $(".log-table").DataTable({
        processing: true,
        serverSide: true,
        responsive: true,
        order: [[ 0, "desc" ]],
        ajax: {
            url: "../log",
            method: "post",
            data: { engine_id: engine_id }
        },
        columnDefs: [{
            targets: [0, 1, 2, 3, 4],
            responsivePriority: 1
        }]
    });

    setInterval(() => {
        if (log_table.page() == 0 && !engine_stopped) {
            log_table.ajax.reload()
        }
    }, 5000);
});