$(document).ready(function() {
    let engine_id = $("#engine_id").val();

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
                success: function(stats) {
                    console.log(stats, Object.keys(stats), _data_entry, stats[data_entry])
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