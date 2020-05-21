$(document).ready(function() {
    let engine_id = $("#engine_id").val();

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

    let make_chart = (selector) => {
        return new Chart(document.querySelector(selector), {
            type: 'line',
            labels: [],
            data: {
                datasets: [{
                    fill: 'origin',
                    backgroundColor: 'rgba(87, 119, 144, 0.7)',
                    data: [],
                }]
            },
            options: {
                legend: {
                    display: false
                },
                elements: {
                    point:{
                        radius: 0
                    }
                }       
            }
        })
    }

    let data_map = {
        "train/train_batch_loss": { chart: make_chart(".graph-batch-loss"), last: 0 },
        "train/train_learning_rate": { chart: make_chart(".graph-learning-rate"), last: 0 },
        "valid/valid_loss": { chart: make_chart(".graph-valid-loss"), last: 0 },
        "valid/valid_score": { chart: undefined, last: 0},
    }

    let updater = undefined;
    let load_data = () => {
        for (data_entry in data_map) {
            let _data_entry = data_entry; // closure
            $.ajax({
                url: `../graph_data`,
                method: "post",
                data: {
                    tag: data_entry,
                    id: engine_id,
                    last: data_map[data_entry].last
                },
                success: function(data) {
                    if (!data) return;
                    
                    let { stats, stopped } = data
                    
                    if (updater && stopped) clearInterval(updater);
                    
                    if (stats[_data_entry]) {
                        let { chart } = data_map[_data_entry];
                        for (let entry of stats[_data_entry]) {
                            if (!(entry.step in chart.data.labels)) {
                                chart.data.labels.push(entry.step);
                                chart.data.datasets[0].data.push(entry.value);

                                if (chart.data.datasets[0].data.length > 250) {
                                    chart.data.labels.shift();
                                    chart.data.datasets[0].data.shift();
                                }

                                stats[_data_entry].last = stats[_data_entry].last + chart.data.datasets[0].data.length
                            }
                        }

                        chart.update();
                    }
                }
            });
        }

        $.ajax({
            url: `../train_status`,
            method: "post",
            data: {
                id: engine_id
            },
            success: function(data) {
                if (data.stats && data.stats['done'] && data.stopped == false) {
                    window.location.href = `../stop/${engine_id}`
                }

                if (data.stats && data.stats['epoch']) {
                    $(".epoch-no").html(data.stats['epoch'])
                }

                if (data.power) {
                    $(".gpu-power").html(data.power);
                }

                if (data.power_reference) {
                    $(".power-reference").html(`(${data.power_reference})`)
                }
            }
        });
    }

    load_data();
    updater = setInterval(load_data, 10000);

    $(".fullscreen-button").on('click', function() {
        $(this).closest('[class*="col-"]').addClass("fullscreen-chart");
    })

    $(".fullscreen-close").on('click', function() {
        $(this).closest('[class*="col-"]').removeClass("fullscreen-chart");
    })

    $(document).ready(function() {
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
            if (log_table.page() == 0) {
                log_table.ajax.reload()
            }
        }, 5000);
    });
});