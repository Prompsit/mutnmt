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
        if (stacks.training) draw_stack(stacks.training, document.querySelector(".training-zone"))
        if (stacks.dev) draw_stack(stacks.dev, document.querySelector(".dev-zone"))
        if (stacks.test) draw_stack(stacks.test, document.querySelector(".test-zone"))
    }
}

let sentences_amount = (amount) => {
    return amount < 1000 ? amount : (amount < 1000000) ? (amount / 1000) + "k" : (amount / 1000000) + "m"
}

let draw_stack = (stack, container) => {
    $(container).find(".area-value-current").html(sentences_amount(stack.sentences));

    distance = 0;
    if (stack.sentences > min_amount) {
        distance = (min_amount * pxps) + ((stack.sentences - min_amount) * pxps_am )
    } else {
        distance = (stack.sentences * pxps )
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
        $(template).find(".area-corpus-amount").html(sentences_amount(corpus.size));
        $(template).find(".area-corpus-name").html(corpus.name);
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
                $(el).find(".corpus-selector-add").off('click').on('click', function(e) {
                    e.preventDefault();
                    let corpus_type = $(el).data("corpus");
                    if (corpora_stacks[corpus_type].sentences + $(el).data("corpus-lines") <= max_amount) {
                        corpora_stacks[corpus_type].sentences += $(el).data("corpus-lines");
                        corpora_stacks[corpus_type].corpora.push({ 
                            id: $(el).data("corpus-id"),
                            name: $(el).data("corpus-name"),
                            size: $(el).data("corpus-lines")
                        });
                        draw_stacks(corpora_stacks);
                    }
                })
            },
            columnDefs: [{
                targets: [0, 1, 2],
                responsivePriority: 1,
                searchable: false,
                sortable: false
            },
            {
                targets: [0, 1],
                searchable: true,
                sortable: true,
                className: "overflow"
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
                data.append(stack + "[]", corpora.id)
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