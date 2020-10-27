$(document).ready(function() {
    let hide_selected = () => {
        $('.compare-btns').addClass("d-none")
        $('.btn-group-toggle').removeClass('d-none');

        const src = $('.engine-select option:selected').attr("data-src");
        const trg = $('.engine-select option:selected').attr("data-trg");
        $('.compare-engine').each(function(i, el) {
            if ($(el).attr("data-engine-id") == $('.engine-select option:selected').val() || 
                ($(el).attr("data-src") != src || $(el).attr("data-trg") != trg)) {
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
        $('.inspect-row').addClass("d-none");
        $(".inspect-compare-content").addClass("d-none");
        $('.inspect-content').html("");

        if ($('.translate-form').attr('data-status') != 'launching') {
            $('.translate-form').attr('data-status', 'launching');

            let engines_id = [$('.engine-select option:selected').val()]
            for (let checkbox of document.querySelectorAll(".compare-engine")) {
                if (checkbox.checked) {
                    engines_id.push(checkbox.getAttribute('data-engine-id'))
                }
            }

            $.ajax({
                url: `compare_text`,
                data: { 
                    "line": $('.translate-text').val(),
                    "engines": engines_id
                },
                method: "post"
            }).done(function(task_id) {
                longpoll(1000, {
                    url: "get_compare",
                    method: "POST",
                    data: { task_id: task_id }
                }, (data) => {
                    if (data.result == 200) {
                        let comparison = data.compare;
                        if (comparison.translations && comparison.translations.length > 0) {
                            for (let translation of comparison.translations) {
                                let template = document.importNode(document.querySelector("#translation-template").content, true);
                                $(template).find(".engine-name").html(translation.name);
                                $(template).find(".user-engine-target").html(translation.text)

                                $(".inspect-compare-content").append(template);
                            }

                            $(".inspect-compare-content").removeClass("d-none");
                        }

                        $(".inspect-row").removeClass("d-none");
                        $('.translate-form').attr('data-status', 'ready');

                        return false;
                    }
                });
            });
        }

        return false;
    }

    $('.compare-engine').on('click', function() {
        $(".inspect-compare-content").addClass("d-none");
        $(".inspect-compare-content .translation-row").remove();
    });

    $('.translate-form').on('submit', function() {
        return onsubmit()
    });
});

$(window).on('unload', function() {
    if (navigator.sendBeacon) {
        navigator.sendBeacon('leave');
    } else {
        $.ajax({ url: `leave`, async: false, type: "post" });
    }
})