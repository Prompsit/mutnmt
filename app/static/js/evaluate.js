$(document).ready(function() {
    let bpl_chart, bleu_dataset, ter_dataset;

    let bpl_table = $(".bleu-line").DataTable({
        lengthMenu: [5, 10, 15, 25, 50, 100],
        columnDefs: [{
            targets: 4,
            render: function(data, type, row) {
                return data + "%"
            }
        }]
    });

    $('.bleu-btn').on('click', function() {
        $('.scores-btn-group .btn').removeClass("active");
        $(this).addClass('active');

        bpl_chart.config.data.datasets[0] = bleu_dataset;
        bpl_chart.update();
    });

    $('.ter-btn').on('click', function() {
        $('.scores-btn-group .btn').removeClass("active");
        $(this).addClass('active');
        console.log(bpl_chart);

        bpl_chart.config.data.datasets[0] = ter_dataset;
        bpl_chart.update();
    });

    $('.evaluate-form').on('submit', function() {
        // Clean previous
        $(".evaluate-results").addClass("d-none");
        $(".evaluate-results-row").empty();
        bpl_table.clear().draw();

        let data = new FormData();
        data.append("mt_file", document.querySelector("#mt_file").files[0])
        data.append("ht_file", document.querySelector("#ht_file").files[0])

        $('.evaluate-status').attr('data-status', 'pending');

        $.ajax({
            url: $(this).attr("action"),
            method: 'POST',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(evaluation) {
                if (evaluation.result == 200) {
                    $(".btn-xlsx-download").attr("href", evaluation.xlsx_url)

                    for (metric of evaluation.metrics) {
                        let template = document.importNode(document.querySelector("#metric-template").content, true);
                        let [min, value, max] = metric.value;
                        let proportion = max - min;
                        let norm_value = (100 * value) / proportion;

                        $(template).find(".metric-name").html(metric.name);
                        $(template).find(".metric-value").html(value);
                        $(template).find(".metric-indicator").css({ "left": `calc(${norm_value}% - 8px)` })
                        $(".evaluate-results-row").append(template);
                    }

                    bpl_table.rows.add(evaluation.spl).draw();

                    $("#blp-graph canvas").remove();
                    $("#blp-graph").append(document.createElement("canvas"));

                    bleu_dataset = {
                        backgroundColor: 'rgba(87, 119, 144, 1)',
                        data: evaluation.spl.map(m => m[3]),
                        categoryPercentage: 1.0,
                        barPercentage: 1.0,
                        label: "Bleu"
                    };

                    ter_dataset = {
                        backgroundColor: '#ffc107',
                        data: evaluation.spl.map(m => m[4]),
                        categoryPercentage: 1.0,
                        barPercentage: 1.0
                    };

                    bpl_chart = new Chart(document.querySelector("#blp-graph").querySelector("canvas"), {
                        type: 'bar',
                        data: {
                            labels: Array.from(Array(evaluation.spl.length), (x, index) => index + 1),
                            datasets: [bleu_dataset]
                        },
                        options: {
                            responsive: true,
                            legend: {
                                display: false
                            },
                            scales: {
                                yAxes: [{
                                    display: true,
                                    ticks: {
                                        suggestedMin: 0, //min
                                        suggestedMax: 100 //max 
                                    },
                                    scaleLabel: {
                                        display: true,
                                        labelString: 'Score'
                                    }
                                }],
                                xAxes: [{
                                    scaleLabel: {
                                        display: true,
                                        labelString: 'Lines'
                                    }
                                }]
                            }
                        }
                    });

                    $('.evaluate-status').attr('data-status', 'none');
                    $(".evaluate-results").removeClass("d-none");
                } else {
                    $('.evaluate-status').attr('data-status', 'error');
                }
            }
        })

        return false;
    });
})