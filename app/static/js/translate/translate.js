$(document).ready(function() {
    let call_count = 0;
    let force_call = false;

    let ontranslate = (e) => {
        call_count += 1;
        if (!force_call && call_count < 5 && $('.live-translate-form').attr('data-status') == 'ready') {
            return;
        }

        call_count = 0;
        force_call = false;

        if ($('.live-translate-form').attr('data-status') == 'ready') {
            if ($('.live-translate-source').val() == "") {
                $('.live-translate-target').html("");
                return;
            }

            $.ajax({
                url: `get`,
                method: "POST",
                data: {
                    text: $('.live-translate-source').val()
                }
            }).done(function(raw) {
                if (raw == "-1") {
                    $('.live-translate-form').attr('data-status', 'error')
                    $('.live-translate-target').html("");
                } else {
                    $('.live-translate-target').html(raw);
                }
            });
        } else if ($('.live-translate-form').attr('data-status') != 'launching') {
            $('.live-translate-form').attr('data-status', 'launching');

            $.ajax({
                url: `attach_engine/${$('.engine-select option:selected').val()}`
            }).done(function(raw) {
                if (raw == "0") {
                    $('.live-translate-form').attr('data-status', 'ready');
                    force_call = true
                    ontranslate()
                } else {
                    $('.live-translate-form').attr('data-status', 'error');
                }
            });
        }

        return false;
    }

    $('.engine-select').on('change', function() {
        $('.live-translate-form').attr('data-status', 'false');

        if ($('.live-translate-source').val() != "") {
            ontranslate()
        }
    });

    let watcher;

    $('.live-translate-source').on('keyup', function() {
        ontranslate();

        if (watcher) clearTimeout(watcher);
        watcher = setTimeout(() => {
            force_call = true
            ontranslate()
        }, 500);

        if ($(this).val() != "") {
            $(this).parent().addClass("filled");
        } else {
            $(this).parent().removeClass("filled");
        }
    });

    $('.engine-relaunch-btn').on('click', function(e) {
        e.preventDefault();
        ontranslate();
    })

    // Live translation
    $('.custom-textarea textarea').on('focus', function() {
        $(this).parent().addClass("focus");
        $(this).parent().find(".custom-textarea-placeholder").addClass("d-none");
    });

    $('.custom-textarea textarea').on('blur', function() {
        $(this).parent().removeClass("focus");
        $(this).parent().find(".custom-textarea-placeholder").removeClass("d-none");
    });
});

$(window).on('unload', function() {
    if (navigator.sendBeacon) {
        navigator.sendBeacon('leave');
    } else {
        $.ajax({ url: `leave`, async: false, type: "post" });
    }
});