$(document).ready(function() {
    let engine_id = $("#engine_id").val();
    let last = 0;

    let chart = new Chart(document.querySelector(".graph-batch-loss"), {
        type: 'line',
        labels: [],
        data: {
            datasets: [{
                fill: 'origin',
                data: [],
            }]
        }
    });

    let load_data = () => {
        $.getJSON(`../graph_data/${engine_id}/${last}`, function(data) {
            if (data["train/train_batch_loss"]) {
                for (let entry of data["train/train_batch_loss"]) {
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
        });
    }

    setInterval(load_data, 10000);
    load_data();
});