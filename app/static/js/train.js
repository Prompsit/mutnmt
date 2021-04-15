// Each sentence makes the counter advance this amount of pixels.
// Basically, (min indicator top offset / min sentences amount)

const min_amounts = { training: 10000, dev: 1000, test: 1000 };
const max_amounts = { training: 500000, dev: 5000, test: 5000 };

let corpora_stacks = {
    training: { sentences: 0, corpora: [] },
    dev: { sentences: 0, corpora: [] },
    test: { sentences: 0, corpora: [] }
}

let draw_stacks = (stacks) => {
    if (stacks) {
        if (stacks.training) draw_stack(stacks, 'training', document.querySelector(".training-zone"))
        if (stacks.dev) draw_stack(stacks, 'dev', document.querySelector(".dev-zone"))
        if (stacks.test) draw_stack(stacks, 'test', document.querySelector(".test-zone"))

        $(".btn-start-training").prop("disabled", (stacks.training.sentences == 0 || stacks.dev.sentences == 0 || stacks.test.sentences == 0));
    }
}

let round = (number) => {
    return parseInt(number);
}

let sentences_amount = (amount) => {
    return amount < 1000 ? amount : (amount < 1000000) ? round(amount / 1000) + "k" : round(amount / 1000000) + "m"
}

let draw_stack = (stacks, tag, container) => {
    let min_amount = min_amounts[tag];
    let max_amount = max_amounts[tag];
    const pxps = 50 / min_amount;
    const pxps_am = ($(container).find(".area-value-max").offset().top - $(container).find(".area-value-min").offset().top) / (max_amount - min_amount);
    const threshold = min_amount * 0.15; // If the current sentence amount is min * threshold, almost there

    let stack = stacks[tag];
    $(container).find(".area-value-current").html(sentences_amount(stack.sentences));

    distance = 0;
    if (stack.sentences > min_amount) {
        distance = (min_amount * pxps) + ((stack.sentences - min_amount) * pxps_am )
    } else {
        distance = (stack.sentences * pxps)
    }

    $(container).find(".area-value-current").css({ top: distance });
    $(container).find(".area-value-bar-fg").css({ height: `${distance}px` })

    if (stack.sentences >= threshold) {
        if (stack.sentences >= min_amount) {
            $(container).attr("data-valid", "yes");
        } else {
            $(container).attr("data-valid", "almost");
        }
    }

    $(container).find(".area-corpora").empty();
    for (let corpus of stack.corpora) {
        let template = document.importNode(document.querySelector("#area-corpus-template").content, true);
        $(template).find(".area-corpus-amount").html(sentences_amount(corpus.selected_size));
        $(template).find(".area-corpus-percent").html(Math.round((corpus.selected_size / corpus.size) * 100))
        $(template).find(".area-corpus-name").html(corpus.name);
        $(template).find(".area-corpus-delete").on('click', function(e) {
            e.preventDefault();
            let index = corpora_stacks[tag].corpora.indexOf(corpus);
            corpora_stacks[tag].sentences -= corpus.selected_size;
            corpora_stacks[tag].corpora.splice(index, 1);
            draw_stacks(corpora_stacks);
            $(".corpus-selector-table").each(function(i, el) {
                $(el).DataTable().draw();
            });
        });

        $(container).find(".area-corpora").append(template);
    }
}

$(document).ready(function() {
    let adjust_languages = (el) => {
        let other = $('.lang_sel').not(el);
        let selected_lang = $(el).find('option:selected').val();
        $(other).find('option').prop('disabled', false)
        $(other).find(`option[value='${selected_lang}']`).prop('disabled', true);

        if ($(other).find('option:selected').val() == selected_lang) {
            $(other).find('option:selected').prop('selected', false);
        }
    }

    let reset_stacks = () => {
        for (let key in corpora_stacks) {
            corpora_stacks[key].sentences = 0
            corpora_stacks[key].corpora = []
        }

        draw_stacks(corpora_stacks);

        $(".corpus-selector-table").each(function(i, el) {
            $(el).DataTable().draw();
        });
    }

    $('.source_lang').on('change', function() {
        adjust_languages(this);
    });

    $('.source_lang, .target_lang').on('change', function() {
        $(".corpus-selector-table").each(function(i, el) {
            $(el).DataTable().draw();
        });

        reset_stacks();
    })

    adjust_languages($('.source_lang'));

    $(".corpus-selector-table").each(function(i, el) {
        $(el).DataTable({
            dom: "ft",
            scrollY: "200px",
            scrollCollapse: true,
            paging: false,
            responsive: true,
            drawCallback: function(settings) {
                let sel_src = $('.source_lang option:selected').val();
                let sel_trg = $('.target_lang option:selected').val();

                $(el).find(".row-corpus").removeClass("d-none");
                $(el).find(".row-corpus").each(function(i, row) {
                    if ( ($(row).attr("data-src") != sel_src || $(row).attr("data-trg") != sel_trg) &&
                            ($(row).attr("data-src") != sel_trg || $(row).attr("data-trg") != sel_src)) {
                        $(row).addClass("d-none");
                    }

                    for (let corpus of corpora_stacks[$(row).attr("data-corpus")].corpora) {
                        if (corpus.id == $(row).attr("data-corpus-id")) {
                            $(row).addClass("d-none");
                        }
                    }

                    if ($(el).find(".row-corpus").length == $(el).find(".row-corpus[class*='d-none']").length) {
                        let template = document.importNode(document.querySelector("#no-corpora-template").content, true);
                        $(row).parent().append(template);
                        return;
                    } else {
                        $(row).parent().find('.no-corpora-row').remove();
                    }

                    let sentences_already_used = 0;
                    for (let stack_name in corpora_stacks) {
                        if (stack_name != $(row).attr("data-corpus")) {
                            for (let corpus of corpora_stacks[stack_name].corpora) {
                                if (corpus.id == $(row).attr("data-corpus-id")) {
                                    sentences_already_used += corpus.selected_size;
                                }
                            }
                        }
                    }

                    let max = parseInt($(row).find(".corpus-selector-add").attr("data-corpus-lines"));
                    let new_max = max - sentences_already_used;

                    if (new_max > 0) {
                        $(row).find(".corpus-selector-lines").attr("max", new_max);
                        $(row).find(".corpus-lines-max").html(sentences_amount(new_max));
                        if (parseInt($(row).find(".corpus-selector-lines").val()) > new_max) {
                            $(row).find(".corpus-selector-lines").val(new_max);
                        }
                    } else {
                        $(row).addClass("d-none");
                    }
                });

                $(el).find(".corpus-selector-add").off('click').on('click', function(e) {
                    let corpus_type = $(this).attr("data-corpus");
                    let corpus_id = $(this).attr("data-corpus-id");
                    let corpus_name = $(this).attr("data-corpus-name");
                    let lines = $(this).attr("data-corpus-lines")
                    let selected_lines = parseInt($(this).closest(".input-group").find(".corpus-selector-lines").val());

                    if (selected_lines) {
                        if (corpora_stacks[corpus_type].sentences + selected_lines > max_amounts[corpus_type]) {
                            selected_lines = max_amounts[corpus_type] - corpora_stacks[corpus_type].sentences;
                        }

                        corpora_stacks[corpus_type].sentences += selected_lines;
                        corpora_stacks[corpus_type].corpora.push({
                            id: corpus_id,
                            name: corpus_name,
                            size: lines,
                            selected_size: selected_lines
                        });

                        draw_stacks(corpora_stacks);

                        $(".corpus-selector-table").each(function(i, _el) {
                            $(_el).DataTable().draw();
                        });
                    }

                    return false;
                });

                $('body').on('click', function (e) {
                    // hide any open popovers when the anywhere else in the body is clicked
                    if (!$(el).find(".corpus-selector-add").is(e.target) && $(el).find(".corpus-selector-add").has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
                        $(el).find(".corpus-selector-add").popover('hide');
                    }
                });
            },
            columnDefs: [{
                targets: [0, 1],
                responsivePriority: 1,
                searchable: true,
                sortable: true,
                className: "overflow"
            },
            {
                targets: 0,
                width: "50%"
            }]
        });
    });

    draw_stacks(corpora_stacks);

    $(".train-form").on('submit', function() {
        $(".token-alert").removeClass("d-none");

        let data = new FormData();
        $(".train-form input").each(function(i, el) {
            if ($(el).attr("name")) {
                data.append($(el).attr("name"), $(el).val());
            }
        });

        $(".train-form select").each(function(i, el) {
            if ($(el).attr("name")) {
                data.append($(el).attr("name"), $(el).find('option:selected').val());
            }
        });

        for (let stack in corpora_stacks) {
            for (let corpora of corpora_stacks[stack].corpora) {
                data.append(stack + "[]", JSON.stringify({ id: corpora.id, size: corpora.selected_size }))
            }
        }

        $.ajax({
            url: $(this).attr("action"),
            method: "POST",
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            success: function(data) {
                if (data.result == 200) {
                    window.location.href = data.launching_url;
                }
            }
        });

        return false;
    });

    $('.train-form').on('reset', function() {
        setTimeout(() => {
            $('.source_lang, .target_lang').trigger('change');
        }, 10);
    });
});