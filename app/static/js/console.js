$(document).ready(function() {
    let engine_id = $("#engine_id").val();
    let last = 0;

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
        "train/train_batch_loss": make_chart(".graph-batch-loss"),
        "train/train_learning_rate": make_chart(".graph-learning-rate"),
        "valid/valid_loss": make_chart(".graph-valid-loss"),
        "valid/valid_score": undefined,
    }

    let load_data = () => {
        $.getJSON(`../graph_data/${engine_id}/${last}`, function(data) {
            for (data_entry in data_map) {
                if (data[data_entry]) {
                    let chart = data_map[data_entry];
                    for (let entry of data[data_entry]) {
                        if (!(entry.step in chart.data.labels)) {
                            chart.data.labels.push(entry.step);
                            chart.data.datasets[0].data.push(entry.value);

                            if (chart.data.datasets[0].data.length > 250) {
                                chart.data.labels.shift();
                                chart.data.datasets[0].data.shift();
                            }

                            last = chart.data.datasets[0].data.length
                        }
                    }

                    chart.update();
                }
            }
        });
    }

    setInterval(load_data, 10000);
    load_data();

    $(".fullscreen-button").on('click', function() {
        $(this).closest('[class*="col-"]').addClass("fullscreen-chart");
    })

    $(".fullscreen-close").on('click', function() {
        $(this).closest('[class*="col-"]').removeClass("fullscreen-chart");
    })
});