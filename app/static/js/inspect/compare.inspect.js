$(document).ready(function() {
    let hide_selected = () => {
        $('.compare-btns').addClass("d-none")
        $('.btn-group-toggle').removeClass('d-none');

        $('.compare-engine').each(function(i, el) {
            if ($(el).attr("data-engine-id") == $('.engine-select option:selected').val()) {
                $(el).closest(".btn-group-toggle").addClass("d-none");
                $(el).prop("checked", false);
            }
        });

        $('.compare-btns').removeClass("d-none")
    }

    $('.engine-select').on('change', function() {
        $('.translate-form').attr('data-status', 'false');
        hide_selected();
    });

    hide_selected();

    let onsubmit = (e) => {
        $(".inspect-compare-content").addClass("d-none");

        $('.user-engine-target').html("");
        $('.engine-target').html("");

        let text = $('.translate-text').val();
        
        let engines_id = [$('.engine-select option:selected').val()]
        for (let checkbox of document.querySelectorAll(".compare-engine")) {
            if (checkbox.checked) {
                engines_id.push(checkbox.getAttribute('data-engine-id'))
            }
        }

        $('.translate-form').attr('data-status', 'launching');
        $(".inspect-compare-content").addClass("d-none");
        $(".inspect-compare-content .translation-row").remove();

        $.ajax({
            url: 'compare/text',
            method: 'post',
            data: {
                text: text, 
                engines: engines_id
            },
            success: function(task_id) {
                longpoll(1000, {
                    url: "get_compare",
                    method: "POST",
                    data: { task_id: task_id }
                }, (data) => {
                    if (data.result == 200) {
                        let inspection = data.compare;
                        $('.google-link').attr('href', `https://translate.google.com/#view=home&op=translate&sl=${inspection['source']}&tl=${inspection['target']}&text=${text}`)
                        $('.deepl-link').attr('href', `https://www.deepl.com/translator#${inspection['source']}/${inspection['target']}/${text}`)

                        for (let translation of inspection.translations) {
                            let template = document.importNode(document.querySelector("#translation-template").content, true);
                            $(template).find(".engine-name").html(translation.name);
                            $(template).find(".user-engine-target").html(translation.text)

                            $(".inspect-compare-content").prepend(template);
                        }

                        $(".inspect-compare-content").removeClass("d-none");
                        $('.translate-form').attr('data-status', 'none');

                        return false;
                    }
                });
            }
        });

        return false;
    }

    $('.translate-form').on('submit', function() {
        return onsubmit()
    });

    $('.compare-engine').on('click', function() {
        $(".inspect-compare-content").addClass("d-none");
        $(".inspect-compare-content .translation-row").remove();
    });
});

$(window).on('unload', function() {
    if (navigator.sendBeacon) {
        navigator.sendBeacon('leave');
    } else {
        $.ajax({ url: `leave`, async: false, type: "post" });
    }
})