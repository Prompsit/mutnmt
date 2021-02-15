$(document).ready(function() {
    let mt_filenames = []
    let ht_filenames = []

    $('.add-mt-btn').on('click', function() {
        let index = $('.mt_file').length + 1
        if (index > 3) return; // No more than 2 MT files

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

    $('.add-ht-btn').on('click', function() {
        let index = $('.ht_file').length + 1
        if (index > 3) return; // No more than 2 MT files

        let template = document.importNode(document.querySelector("#ht-file-template").content, true);
        $(template).find('.ht-file-row').attr('id', `ht-file-row-${index}`)
        $(template).find('.ht-file').attr('id', `ht-file-${index}`).attr('name', `ht-file-${index}`)
        $(template).find('label').attr('for', `ht-file-${index}`);

        $(template).find('.remove-ht-btn').on('click', function() {
            $(`#ht-file-row-${index}`).remove()
        });

        $(template).find('.custom-file input[type=file]').each(function (i, el) {
            if (el.files.length > 0) {
                $(el).closest(".custom-file").find(".custom-file-label").html(el.files[0].name);
            }
        });
        
        $(template).find('.custom-file input[type=file]').on('change', function() {
            $(this).closest(".custom-file").find(".custom-file-label").html(this.files[0].name);
        });

        $('.ht-file-container').append(template);
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
        $(".evaluate-hint").addClass("d-none");
        
        // Clean previous
        $(".evaluate-results").addClass("d-none");
        $(".evaluate-results-row").empty();
        $(".chart-select").empty();
        $('.results-select').empty();

        if (bpl_table) bpl_table.clear().draw();

        let data = new FormData();
        data.append("source_file", document.querySelector("#source_file").files[0])

        mt_filenames = []
        $(".mt_file").each(function(i, el) {
            if (el.files.length > 0) {
                data.append("mt_files[]", el.files[0])
                mt_filenames.push(el.files[0].name)
            }
        });

        ht_filenames = []
        $(".ht_file").each(function(i, el) {
            if (el.files.length > 0) {
                data.append("ht_files[]", el.files[0]);
                ht_filenames.push(el.files[0].name);
            }
        });

        $('.evaluate-status').attr('data-status', 'pending');

        let show_results = (evaluation, task_id, mt_ix, ht_ix) => {            
            // Clean previous
            $(".evaluate-results").addClass("d-none");
            $(".evaluate-results-row").empty();
            $(".chart-select").empty();

            if (bpl_table) bpl_table.destroy();

            $(".btn-xlsx-download").attr("href", `download/${task_id}/${ht_ix}`);

            for (let _eval of evaluation.evals[mt_ix][ht_ix]) {
                if (_eval.is_metric) {
                    let template = document.importNode(document.querySelector("#metric-template").content, true);
                    let [min, value, max] = _eval.value;
                    let reversed = (min > max)
                    
                    if (reversed) {
                        // Normally, min is the worst value and max is the best
                        // In the case those values come reversed (for example [100, 50, 0])
                        // it means that min is the best value and max is the worst (e.g. TER scores)
                        // So we reverse the progress bar in the UI

                        $(template).find(".metric-hint").addClass("reversed");

                        let min_aux = min;
                        min = max;
                        max = min_aux;
                    }

                    let proportion = max - min;
                    let norm_value = (100 * (value > max ? max : value < min ? min : value)) / proportion;

                    $(template).find(".metric-name").html(_eval.name);
                    $(template).find(".metric-value").html(value);
                    $(template).find(".metric-indicator").css({ "left": `calc(${norm_value}% - 8px)` })
                    $(".evaluate-results-row").append(template);
                } else {
                    let [min, value, max] = _eval.value;
                    if (_eval.name == "MT") {
                        $(".mt-lexical-value").html(value);
                    } else if (_eval.name == "REF") {
                        $(".ht-lexical-value").html(value);
                    }
                }
            }

            $(".chart-container div").remove();
            $(".chart-container").append(document.createElement("div"));

            let file_series = { bleu: [], ter: [] };
            file_series['bleu'] = evaluation.spl[ht_ix].map(m => parseFloat(m[5][mt_ix]['bleu']))
            file_series['ter'] = evaluation.spl[ht_ix].map(m => parseFloat(m[5][mt_ix]['ter']))

            bpl_chart = new ApexCharts(document.querySelector('.chart-container div'), {
                series: [{
                    name: 'BLEU',
                    data: file_series['bleu'].splice(0, 100)
                },
                {
                    name: 'TER',
                    data: file_series['ter'].splice(0, 100).map(m => (-1) * m)
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
                colors: ['rgba(87, 119, 144, 1)', '#ffc107'],
                tooltip: {
                    y: {
                        formatter: function(value, { _, seriesIndex }) {
                            if (seriesIndex == 1) { // Series 1 is TER
                                return parseFloat(value * -1).toFixed(2) + "%";
                            } else {
                                return parseFloat(value).toFixed(2);
                            }
                        }
                    }
                }
            });

            $('.evaluate-status').attr('data-status', 'none');
            $(".evaluate-results").removeClass("d-none");
            
            bpl_chart.render();

            $('.page-number').attr('max', evaluation.spl[ht_ix].length);
            bpl_table = $(".bleu-line").DataTable({
                data: evaluation.spl[ht_ix],
                dom: "tp",
                pageLength: 1,
                responsive: true,
                pagingType: "full",
                drawCallback: function(settings) {
                    let api = this.api()
                    let rows = api.rows({ page: 'current' }).nodes();
                    let row_data = api.rows({ page: 'current' }).data();

                    $('.page-number').val(api.page() + 1);
                    
                    rows.each(function(row, i) {
                        let data = row_data[i];
                        let sentences_data = data[5];
                    
                        if (data.length > 6) {
                            let template = document.importNode(document.querySelector("#sentences-view-template").content, true);
                            $(template).find(".sentences-view-source").html(data[6])
                            $(row).before(template);
                        }

                        let ix = 1;
                        for (sentence_data of sentences_data) {
                            let mt_template = document.importNode(document.querySelector("#sentences-view-mt-template").content, true);
                            $(mt_template).find(".sentences-view-mt-index").html(ix);
                            $(mt_template).find(".sentences-view-mt").html(sentence_data.text);
                            $(mt_template).find(".sentences-view-bleu").html(sentence_data.bleu);
                            $(mt_template).find(".sentences-view-ter").html(sentence_data.ter);
                            $(row).before(mt_template);
                            
                            ix++;
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

            $('.page-btn').on('click', function() {
                let page_val = parseInt($('.page-number').val()) - 1;
                bpl_table.page(page_val).draw(false);
            });
        }

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

                            for (let i = 0; i < mt_filenames.length; i++) {
                                let opt_el = document.createElement('option');
                                $(opt_el).attr("value", i).html(mt_filenames[i]);
                                $(".results-mt-select").append(opt_el);
                            }

                            for (let i = 0; i < ht_filenames.length; i++) {
                                let opt_el = document.createElement('option');
                                $(opt_el).attr("value", i).html(ht_filenames[i]);
                                $(".results-ht-select").append(opt_el);
                            }

                            $(".btn-xlsx-download").attr("href", `download/${data.task_id}/0`)

                            show_results(evaluation, data.task_id, 0, 0);

                            $('.results-select').off('change').on('change', function() {
                                show_results(evaluation, data.task_id, $(".results-mt-select option:selected").val(), $(".results-ht-select option:selected").val());
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
});