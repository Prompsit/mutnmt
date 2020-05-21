// Each sentence makes the counter advance this amount of pixels.
// Basically, (min indicator top offset / min sentences amount)
const min_amount = 10000;
const max_amount = 200000;
const pxps = 50 / min_amount;
const pxps_am = ($(".area-value-max").offset().top - $(".area-value-min").offset().top) / (max_amount - min_amount);
const threshold = min_amount * 0.15; // If the current sentence amount is min * threshold, almost there

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
    }
}

let sentences_amount = (amount) => {
    return amount < 1000 ? amount : (amount < 1000000) ? (amount / 1000) + "k" : (amount / 1000000) + "m"
}

let draw_stack = (stacks, tag, container) => {
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
    $(".corpus-selector-table").each(function(i, el) {
        $(el).DataTable({
            dom: "ft",
            scrollY: "200px",
            scrollCollapse: true,
            paging: false,
            responsive: true,
            drawCallback: function(settings) {
                $(".row-corpus").removeClass("d-none");
                $(".row-corpus").each(function(i, row) {
                    for (let corpus of corpora_stacks[$(row).attr("data-corpus")].corpora) {
                        if (corpus.id == $(row).attr("data-corpus-id")) {
                            $(row).addClass("d-none");
                        }
                    }
                })


                $(el).find(".corpus-selector-add").off('click').on('click', function(e) {
                    let corpus_type = $(this).attr("data-corpus");
                    let corpus_id = $(this).attr("data-corpus-id");
                    let corpus_name = $(this).attr("data-corpus-name");
                    let lines = $(this).attr("data-corpus-lines")
                    let selected_lines = parseInt($(this).closest(".input-group").find(".corpus-selector-lines").val());

                    if (corpora_stacks[corpus_type].sentences + selected_lines <= max_amount) {
                        corpora_stacks[corpus_type].sentences += selected_lines;
                        corpora_stacks[corpus_type].corpora.push({ 
                            id: corpus_id,
                            name: corpus_name,
                            size: lines,
                            selected_size: selected_lines
                        });
                        draw_stacks(corpora_stacks);
                    }

                    $(el).DataTable().draw();

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
            success: function(url) {
                window.location.href = url;
            }
        })

        return false;
    })
});