$(document).ready(function() {
    let source_file = false;

    $('.source-text-control .btn').on('click', function() {
        $('.source-text-control .btn').addClass('d-none');
        $('.source-text-content').removeClass('d-none');
        source_file = true;
    });

    $('.source-text-close').on('click', function() {
        $('.source-text-control .btn').removeClass('d-none');
        $('.source-text-content').addClass('d-none');
        source_file = false;
    });

    let bpl_chart, bleu_dataset, ter_dataset;

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

    let bpl_table;
    $('.evaluate-form').on('submit', function() {
        // Clean previous
        $(".evaluate-results").addClass("d-none");
        $(".evaluate-results-row").empty();
        $(".score-table").addClass("d-none");
        if (bpl_table) bpl_table.destroy();

        let bpl_table_el = (source_file) ? ".bleu-line-source" : ".bleu-line"
        $(bpl_table_el).removeClass("d-none");

        bpl_table = $(bpl_table_el).DataTable({
            lengthMenu: [5, 10, 15, 25, 50, 100],
            columnDefs: [{
                targets: [1, 2, 3],
                className: "overflow"
            },
            {
                targets: (source_file) ? 5 : 4,
                render: function(data, type, row) {
                    return data + "%"
                }
            }]
        });

        let data = new FormData();
        data.append("mt_file", document.querySelector("#mt_file").files[0])
        data.append("ht_file", document.querySelector("#ht_file").files[0])
        if (source_file) data.append("source_file", document.querySelector("#source_file").files[0])

        $('.evaluate-status').attr('data-status', 'pending');

        $.ajax({
            url: $(this).attr("action"),
            method: 'POST',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(task_id) {
                longpoll(2000, {
                    url: "get_evaluation",
                    method: "POST",
                    data: { task_id: task_id }
                }, (data) => {
                    if (data.result == 200) {
                        let evaluation = data.evaluation;

                        $(".btn-xlsx-download").attr("href", `download/${task_id}`)

                        for (metric of evaluation.metrics) {
                            let template = document.importNode(document.querySelector("#metric-template").content, true);
                            let [min, value, max] = metric.value;
                            let reversed = (min > max)
                            
                            if (reversed) {
                                // Normally, min is the worst value and max is the best
                                // In the case those values come reversed (for example [100, 50, 0])
                                // it means that min is the best value and max is the worst (e.g. TER scores)
                                // So we reverse the progress bar in the UI

                                $(template).find(".metric-hint .low-zone").before($(template).find(".metric-hint .high-zone"))
                                $(template).find(".metric-hint .low-zone").before($(template).find(".metric-hint .medium-zone"))

                                let min_aux = min;
                                min = max;
                                max = min_aux;
                            }

                            let proportion = max - min;
                            let norm_value = (100 * value) / proportion;

                            $(template).find(".metric-name").html(metric.name);
                            $(template).find(".metric-value").html(value);
                            $(template).find(".metric-indicator").css({ "left": `calc(${norm_value}% - 8px)` })
                            $(".evaluate-results-row").append(template);
                        }

                        bpl_table.rows.add(evaluation.spl).draw();

                        $(".chart-container div").remove();
                        $(".chart-container").append(document.createElement("div"));

                        console.log(evaluation.spl.map(m => parseFloat(m[(source_file) ? 4 : 3])))
                        console.log(evaluation.spl.map(m => parseFloat(m[(source_file) ? 5 : 4])))

                        bpl_chart = new ApexCharts(document.querySelector('.chart-container div'), {
                            series: [{
                                name: 'BLEU',
                                data: evaluation.spl.map(m => parseFloat(m[(source_file) ? 4 : 3]))
                            },
                            {
                                name: 'TER',
                                data: evaluation.spl.map(m => (-1) * parseFloat(m[(source_file) ? 5 : 4]))
                            }],
                            chart: {
                                type: 'bar',
                                width: '100%',
                                height: 500,
                                stacked: true,
                                toolbar: {
                                    show: true
                                },
                                zoom: {
                                    enabled: true
                                }
                            },
                            plotOptions: {
                                bar: {
                                    colors: {
                                        ranges: [{
                                            from: -100,
                                            to: 0,
                                            color: '#ffc107'
                                        },
                                        {
                                            from: 0,
                                            to: 100,
                                            color: 'rgba(87, 119, 144, 1)'
                                        }]
                                    }
                                }
                            },
                            dataLabels: { enabled: false },
                            yaxis: {
                                max: 100,
                                min: -100
                            },
                            colors: ['rgba(87, 119, 144, 1)', '#ffc107']
                        });

                        
                        $('.evaluate-status').attr('data-status', 'none');
                        $(".evaluate-results").removeClass("d-none");
                        
                        bpl_chart.render();

                        return false;
                    }
                });
            }
        })

        return false;
    });
})