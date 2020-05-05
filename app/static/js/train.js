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

    if (stack.sentences > min_amount) {
        $(container).find(".area-value-current").css({ top: (min_amount * pxps) + ((stack.sentences - min_amount) * pxps_am )});
    } else {
        $(container).find(".area-value-current").css({ top: (stack.sentences * pxps )});
    }

    if (stack.sentences >= threshold) {
        if (stack.sentences >= min_amount) {
            $(container).find(".area-value-current").attr("data-valid", "yes");
        } else {
            $(container).find(".area-value-current").attr("data-valid", "almost");
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
    $(".corpus-selector-table").DataTable({
        dom: "ft",
        scrollY: "200px",
        scrollCollapse: true,
        paging: false,
        responsive: true,
        drawCallback: function(settings) {
            $(".corpus-selector-add").off('click').on('click', function(e) {
                e.preventDefault();
                let corpus_type = $(this).data("corpus");
                if (corpora_stacks[corpus_type].sentences + $(this).data("corpus-lines") <= max_amount) {
                    corpora_stacks[corpus_type].sentences += $(this).data("corpus-lines");
                    corpora_stacks[corpus_type].corpora.push({ 
                        id: $(this).data("corpus-id"),
                        name: $(this).data("corpus-name"),
                        size: $(this).data("corpus-lines")
                    });
                    draw_stacks(corpora_stacks);
                }
            })
        },
        columnDefs: [{
            targets: [0, 1, 2],
            responsivePriority: 1
        },
        {
            targets: [0, 1],
            searchable: true,
            sortable: true
        }]
    });

    draw_stacks(corpora_stacks);

    $(".train-form").on('submit', function() {
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