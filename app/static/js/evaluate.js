$(document).ready(function() {
    let source_file = false;
    let file_names = []

    $('.source-text-control .btn').on('click', function() {
        $('.source-text-control').addClass('d-none');
        $('.source-text-content').removeClass('d-none');
        source_file = true;
    });

    $('.source-text-close').on('click', function() {
        $('.source-text-control').removeClass('d-none');
        $('.source-text-content').addClass('d-none');
        source_file = false;
    });

    $('.add-mt-btn').on('click', function() {
        let index = $('.mt-file').length + 1
        let template = document.importNode(document.querySelector("#mt-file-template").content, true);
        $(template).find('.mt-file-row').attr('id', `mt-file-row-${index}`)
        $(template).find('.mt-file').attr('id', `mt-file-${index}`).attr('name', `mt-file-${index}`)
        $(template).find('label').attr('for', `mt-file-${index}`);

        $(template).find('.remove-mt-btn').on('click', function() {
            $(`#mt-file-row-${index}`).remove()
        });

        $(template).find('.custom-file input[type=file]').each(function (i, el) {
            if (el.files.length > 0) {
                $(el).closest(".custom-file").find(".custom-file-label").html(el.files[0].name);
            }
        });
        
        $(template).find('.custom-file input[type=file]').on('change', function() {
            $(this).closest(".custom-file").find(".custom-file-label").html(this.files[0].name);
        });

        $('.mt-file-container').append(template);
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
        if (bpl_table) bpl_table.destroy();

        let data = new FormData();
        data.append("ht_file", document.querySelector("#ht_file").files[0])
        if (source_file) data.append("source_file", document.querySelector("#source_file").files[0])

        file_names = []
        $(".mt_file").each(function(i, el) {
            if (el.files.length > 0) {
                data.append("mt_files[]", el.files[0])
                file_names.push(el.files[0].name)
            }
        });

        $('.evaluate-status').attr('data-status', 'pending');

        $.ajax({
            url: $(this).attr("action"),
            method: 'POST',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(data) {
                if (data.result == 200) {
                    longpoll(2000, {
                        url: "get_evaluation",
                        method: "POST",
                        data: { task_id: data.task_id }
                    }, (data) => {
                        if (data.result == 200) {
                            let evaluation = data.evaluation;

                            $(".btn-xlsx-download").attr("href", `download/${data.task_id}`)

                            let i = 0;
                            for (metrics of evaluation.metrics) {
                                let title_template = document.importNode(document.querySelector("#metric-title-template").content, true);
                                $(title_template).find('.metric-title').html(file_names[i]);
                                $(".evaluate-results-row").append(title_template);
                                i++;
                                
                                for (metric of metrics) {
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
                            }

                            $(".chart-container div").remove();
                            $(".chart-container").append(document.createElement("div"));

                            bpl_chart = new ApexCharts(document.querySelector('.chart-container div'), {
                                series: [{
                                    name: 'BLEU',
                                    data: evaluation.spl.map(m => parseFloat(m[5]['bleu']))
                                },
                                {
                                    name: 'TER',
                                    data: evaluation.spl.map(m => (-1) * parseFloat(m[5]['ter']))
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
                                    min: -100,
                                    labels: {
                                        formatter: (val) => {
                                            if (val % parseInt(val) == 0) return parseInt(val)
                                            return val.toFixed(2)
                                        }
                                    }
                                },
                                colors: ['rgba(87, 119, 144, 1)', '#ffc107']
                            });

                            
                            $('.evaluate-status').attr('data-status', 'none');
                            $(".evaluate-results").removeClass("d-none");
                            
                            bpl_chart.render();

                            bpl_table = $(".bleu-line").DataTable({
                                data: evaluation.spl,
                                dom: "tp",
                                pageLength: 1,
                                drawCallback: function(settings) {
                                    let api = this.api()
                                    let rows = api.rows({ page: 'current' }).nodes();
                                    let row_data = api.rows({ page: 'current' }).data();
                                    rows.each(function(row, i) {
                                        let data = row_data[i];
                                        let sentences_data = data[5];
                                    
                                        if (data.length > 6) {
                                            let template = document.importNode(document.querySelector("#sentences-view-template").content, true);
                                            $(template).find(".sentences-view-source").html(data[6])
                                            $(row).before(template);
                                        }

                                        for (sentence_data of sentences_data) {
                                            let mt_template = document.importNode(document.querySelector("#sentences-view-mt-template").content, true);
                                            $(mt_template).find(".sentences-view-mt").html(sentence_data.text);
                                            $(mt_template).find(".sentences-view-bleu").html(sentence_data.bleu);
                                            $(mt_template).find(".sentences-view-ter").html(sentence_data.ter);
                                            $(row).after(mt_template);
                                        }

                                        $(".score-table-line-no").html(data[4]);

                                        this.columns.adjust();
                                    });
                                },
                                columnDefs: [{
                                    targets: '_all',
                                    orderable: false    
                                },
                                {
                                    targets: [0, 1],
                                    className: "overflow"
                                },
                                {
                                    targets: 0,
                                    render: function(data, type, row) {
                                        return "<strong>" + data + "</strong>"
                                    }
                                }]
                            });

                            return false;
                        }
                    });
                } else {
                    $('.evaluate-status').attr('data-status', 'error');
                }
            }
        });

        return false;
    });
})